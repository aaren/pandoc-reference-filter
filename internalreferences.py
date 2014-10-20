import re

import pandocfilters as pf

figure_styles = {'latex': ('\n'
                           '\\begin{{figure}}[htbp]\n'
                           '\\centering\n'
                           '\\includegraphics{{{filename}}}\n'
                           '\\caption{{{caption}}}\n'
                           '\\label{{{label}}}\n'
                           '\\end{{figure}}\n'),

                 'html': ('\n'
                           '<div class="figure" id="{id}" {classes} {keys}>\n'
                           '<img src="{filename}" alt="{alt}" />'
                           '<p class="caption">{caption}</p>\n'
                           '</div>\n'),

                 'html5': ('\n'
                          '<figure id="{id}" {classes} {keys}>\n'
                          '<img src="{filename}" alt="{alt}" />\n'
                          '<figcaption>{caption}</figcaption>\n'
                          '</figure>'),

                 'markdown': ('\n'
                              '<div id="{id}">\n'
                              '![{caption}]({filename})\n'
                              '\n'
                              '</div>\n')
                 }

# replacement text to use for in text internal links
# that refer to various types of thing, in different
# output formats
latex_link = '{pre}\\autoref{{{label}}}{post}'
html_link = '{pre}<a href="#{label}">{text}</a>{post}'
markdown_link = '{pre}[{text}](#{label}){post}'

latex_math_link = '{pre}\\autoref{{{label}}}{post}'
html_math_link = '{pre}Equation \\eqref{{{label}}}{post}'
markdown_math_link = '{pre}Equation $\\eqref{{{label}}}${post}'

link_styles = {
    'latex': {'figure': latex_link,
              'section': latex_link,
              'math': latex_math_link},
    'html': {'figure': html_link,
             'section': html_link,
             'math': html_math_link},
    'html5': {'figure': html_link,
              'section': html_link,
              'math': html_math_link},
    'markdown': {'figure': markdown_link,
                 'section': markdown_link,
                 'math': markdown_math_link}
}


# http://cdn.mathjax.org/mathjax/latest/test/sample-eqrefs.html
# mathjax claims that you can get equation references on regular
# display math but I'm only finding it to work on equation
# environments.
# No, you can, just need autoequations: 'all' rather than 'AMS'


class AttributeParser(object):
    """Parser for pandoc block attributes.

    usage:
        attrs = '#id .class1 .class2 key=value'
        parser = AttributeParser()
        parser.parse(attrs)
        >>> {'id': 'id', 'classes': ['class1', 'class2'], 'key'='value'}
    """
    spnl = ' \n'

    @staticmethod
    def isid(string):
        return string.startswith('#')

    @staticmethod
    def isclass(string):
        return string.startswith('.')

    @staticmethod
    def iskv(string):
        return ('=' in string)

    @staticmethod
    def isspecial(string):
        return '-' == string

    @classmethod
    def parse(self, attr_string):
        attr_string = attr_string.strip('{}')
        split_regex = r'''((?:[^{separator}"']|"[^"]*"|'[^']*')+)'''.format
        splitter = re.compile(split_regex(separator=self.spnl))
        attrs = splitter.split(attr_string)[1::2]

        id = [a[1:] for a in attrs if self.isid(a)]
        classes = [a[1:] for a in attrs if self.isclass(a)]
        kvs = [a.split('=', 1) for a in attrs if self.iskv(a)]
        special = ['unnumbered' for a in attrs if self.isspecial(a)]

        attr_dict = {k: v for k, v in kvs}
        attr_dict['id'] = id[0] if id else ""
        attr_dict['classes'] = classes + special

        return attr_dict

attr_parser = AttributeParser()


def rawlatex(s):
    return pf.RawInline('latex', s)


def rawhtml(s):
    return pf.RawInline('html', s)


def rawmarkdown(s):
    return pf.RawInline('markdown', s)


def isheader(key, value):
    return (key == 'Header')


def islabeledmath(key, value):
    return (key == 'Math' and re.search(r'\\label{\S*}', value[1]))


# pattern that matches #reflink
# only allow characters that we can have in latex labels
# currently have to be after whitespace
# terminated by whitespace, period or backslash
imp_reflink_pattern = re.compile(r'([\s]?)(#[\w:&^]+)([\. \t\\]?)')


def isinternalref(key, value):
    # This can fall over if we don't create_figures from our
    # special attr images first - it can match #id in the attrs
    return key == 'Str' and imp_reflink_pattern.match(value)

# define a new type for internal references [pre, label, post]
InternalRef = pf.elt('InternalRef', 3)


def isattr(string):
    return string.startswith('{') and string.endswith('}')


def isfigure(key, value):
    return (key == 'Para' and len(value) == 2 and value[0]['t'] == 'Image')


def isattrfigure(key, value):
    return (key == 'Para'
            and value[0]['t'] == 'Image'
            and isattr(pf.stringify(value[1:])))


# define a new Figure type - an image with attributes
Figure = pf.elt('Figure', 3)  # caption, target, attrs


def isFigure(key, value):
    return key == 'Figure'


def create_figures(key, value, format, metadata):
    """Convert Images with attributes to Figures.

    Images are [caption, (filename, title)].

    Figures are [caption, (filename, title), attrs].

    This isn't a supported pandoc type, we just use it internally.
    """
    if isattrfigure(key, value):
        image = value[0]
        attr_string = pf.stringify(value[1:])

        caption, target = image['c']
        attrd = attr_parser.parse(attr_string)
        attrs = pf.attributes(attrd)

        return Figure(caption, target, attrs)


class ReferenceManager(object):
    """Internal reference manager.

    Stores all referencable objects in the document, with a label
    and a type, then allows us to look up the object and type using
    a label.

    This means that we can determine the appropriate replacement
    text of any given internal reference (no need for e.g. 'fig:' at
    the start of labels).
    """
    section_count = [1, 1, 1, 1, 1, 1]
    secdict = {}

    figure_count = 1
    equation_count = 1
    refdict = {}

    replacements = {'figure': 'Figure {}',
                    'section': 'Section {}',
                    'math': 'Equation {}'}

    formats = ('html', 'html5', 'markdown', 'latex')

    def increment_section_count(self, header_level):
        """Changing the section count is dependent on the header level.

        When we add to the section count, we want to reset the
        count for all headers at a higher header level than that
        given, increment the count at the header level, and leave
        the same all lower levels.
        """
        self.section_count[header_level - 1] += 1
        for i, _ in enumerate(self.section_count[header_level:]):
            self.section_count[header_level + i] = 0

    def format_section_count(self, header_level):
        """Format the section count for a given header level,
        leaving off info from higher header levels,

        e.g. section_count = [1, 2, 4, 3]
        format_section_count(3) == '1.2.4'
        """
        return '.'.join(str(i) for i in self.section_count[:header_level])

    def consume_references(self, key, value, format, metadata):
        """Find all figures and sections that can be referenced in
        the document and replace them with appropriate text whilst
        appending to the internal refdict.
        """
        if isFigure(key, value):
            return self.figure_replacement(key, value, format, metadata)
        elif isheader(key, value) and format in self.formats:
            return self.section_replacement(key, value, format, metadata)
        elif islabeledmath(key, value):
            return self.math_replacement(key, value, format, metadata)

    def figure_replacement(self, key, value, format, metadata):
        """Replace figures with appropriate representation and
        append info to the refdict.

        This works with Figure, which is our special type for images
        with attributes. This allows us to set an id in the attributes.

        The other way of doing it would be to pull out a '\label{(.*)}'
        from the caption of an Image and use that to update the refdict.
        """
        _caption, (filename, target), (id, classes, kvs) = value
        scaption = pf.stringify(_caption)

        caption = 'Figure {n}: {caption}'.format(n=self.figure_count,
                                                 caption=scaption)

        class_str = 'class="{}"'.format(' '.join(classes)) if classes else ''
        key_str = ' '.join('{}={}'.format(k, v) for k, v in kvs)

        self.refdict[id] = {'type': 'figure',
                            'id': self.figure_count}

        self.figure_count += 1

        if format == 'markdown':
            figure = figure_styles[format].format(id=id,
                                            caption=caption,
                                            filename=filename)

            return pf.Para([rawmarkdown(figure)])

        elif format == 'html':
            figure = figure_styles[format].format(id=id,
                                        classes=class_str,
                                        keys=key_str,
                                        filename=filename,
                                        alt=caption,
                                        caption=caption)
            return pf.Para([rawhtml(figure)])

        elif format == 'html5':
            figure = figure_styles[format].format(id=id,
                                         classes=class_str,
                                         keys=key_str,
                                         filename=filename,
                                         alt=caption,
                                         caption=caption)
            return pf.Para([rawhtml(figure)])

        elif format == 'latex':
            figure = figure_styles[format].format(filename=filename,
                                         caption=scaption,
                                         label=id)
            return pf.Para([rawlatex(figure)])

    def section_replacement(self, key, value, format, metadata):
        """Replace sections with appropriate representation and
        append info to the refdict.
        """
        level, attr, text = value

        secn = self.format_section_count(level)
        self.increment_section_count(level)

        label = attr[0]
        self.refdict[label] = {'type': 'section',
                                'id': secn}

        pretext = '{}:'.format(secn)
        pretext = [pf.Str(pretext), pf.Space()]

        if format in ('html', 'html5', 'markdown'):
            return pf.Header(level, attr, pretext + text)

        elif format == 'latex':
            # have to do this to get rid of hyperref
            return pf.Header(level, attr, text)

    def math_replacement(self, key, value, format, metadata):
        """Math should not need replacing as mathjax / latex will
        take care of any references. All we do is append to the
        refdict and increment an equation count (which nothing uses
        yet).
        """
        mathtype, math = value
        label, = re.search(r'\\label{([\w:&^]+)}', math).groups()
        self.refdict[label] = {'type': 'math',
                               'id': self.equation_count}
        self.equation_count += 1
        return None

    def create_internal_refs(self, key, value, format, metadata):
        """Convert #label in the text into InternalRef, but only if the
        label is in the refdict.
        """
        if isinternalref(key, value):
            pre, link, post = imp_reflink_pattern.match(value).groups()
            label = link.lstrip('#')
            if label in self.refdict:
                return InternalRef(pre, label, post)

    def convert_internal_refs(self, key, value, format, metadata):
        """Convert all internal links from '#blah' into format
        specified in self.replacements.
        """
        if key != 'InternalRef':
            return None

        else:
            pre, label, post = value

        rtype = self.refdict[label]['type']
        n = self.refdict[label]['id']
        text = self.replacements[rtype].format(n)

        if format in ('html', 'html5'):
            return rawhtml(link_styles[format][rtype].format(text=text,
                                                             label=label,
                                                             pre=pre,
                                                             post=post))

        elif format == 'markdown':
            return rawmarkdown(link_styles[format][rtype].format(text=text,
                                                                 label=label,
                                                                 pre=pre,
                                                                 post=post))
        elif format == 'latex':
            return rawlatex(link_styles[format][rtype].format(label=label,
                                                              pre=pre,
                                                              post=post))
        else:
            return None

    @property
    def reference_filter(self):
        return [create_figures,
                self.consume_references,
                self.create_internal_refs,
                self.convert_internal_refs]


def toJSONFilter(actions):
    """Modified from pandocfilters to accept a list of actions (to
    apply in series) as well as a single action.

    Converts an action into a filter that reads a JSON-formatted
    pandoc document from stdin, transforms it by walking the tree
    with the action, and returns a new JSON-formatted pandoc document
    to stdout.

    The argument is a function action(key, value, format, meta),
    where key is the type of the pandoc object (e.g. 'Str', 'Para'),
    value is the contents of the object (e.g. a string for 'Str',
    a list of inline elements for 'Para'), format is the target
    output format (which will be taken for the first command line
    argument if present), and meta is the document's metadata.

    If the function returns None, the object to which it applies
    will remain unchanged.  If it returns an object, the object will
    be replaced.  If it returns a list, the list will be spliced in to
    the list to which the target object belongs.  (So, returning an
    empty list deletes the object.)
    """
    doc = pf.json.loads(pf.sys.stdin.read())
    if len(pf.sys.argv) > 1:
        format = pf.sys.argv[1]
    else:
        format = ""

    if type(actions) is type(toJSONFilter):
        altered = pf.walk(doc, actions, format, doc[0]['unMeta'])
    elif type(actions) is list:
        altered = doc
        for action in actions:
            altered = pf.walk(altered, action, format, doc[0]['unMeta'])

    pf.json.dump(altered, pf.sys.stdout)


def suppress_input_cells(key, value, format, metadata):
    """For use with notedown. Suppresses code cells that have the
    attribute '.input'.
    """
    if format == 'latex' and key == 'CodeBlock' and 'input' in value[0][1]:
        return pf.Null()


def main():
    refmanager = ReferenceManager()
    toJSONFilter(refmanager.reference_filter + [suppress_input_cells])

if __name__ == '__main__':
    main()
