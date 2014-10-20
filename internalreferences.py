import re

import pandocfilters as pf

latex_figure = """
\\begin{{figure}}[htbp]
\\centering
\\includegraphics{{{filename}}}
\\caption{{{caption}}}
\\label{{{label}}}
\\end{{figure}}"""

html5_figure = """
<figure id="{id}" {classes} {keys}>
<img src="{filename}" alt="{alt}" />
<figcaption>{caption}</figcaption>
</figure>"""

html_figure = """
<div class="figure" id="{id}" {classes} {keys}>
<img src="{filename}" alt="{alt}" /><p class="caption">{caption}</p>
</div>
"""

markdown_figure = """
<div id="{id}">
![{caption}]({filename})

</div>
"""

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


def isfigure(key, value):
    return (key == 'Para' and len(value) == 2 and value[0]['t'] == 'Image')


def islabeledmath(key, value):
    return (key == 'Math' and re.search(r'\\label{\S*}', value[1]))


def isattrfigure(key, value):
    return (key == 'Para'
            and value[0]['t'] == 'Image'
            and isattr(pf.stringify(value[1:])))


# pattern that matches #reflink
# only allow characters that we can have in latex labels
# currently have to be after whitespace
# terminated by whitespace, period or backslash
imp_reflink_pattern = re.compile(r'([\s]?)(#[\w:&^]+)([\. \t\\]?)')


def isinternallink(key, value):
    # FIXME: this will break with our image attribute syntax.
    # We have implemented attributes on images, but pandoc doesn't
    # recognise this so they get parsed as Str. We can define an id
    # as '#id' anywhere in the attributes, and this will currently
    # only work if it is defined at the start (after the initial
    # '{').
    #
    # We need to find a way to allow #id anywhere in the attributes.
    # Perhaps give the image attributes an interim key?
    # Can we see if the Str is contained within something that
    # matches isattrfigure?
    #
    # Actually, we're ok as long as 'figures' get parsed out and
    # dealt with first. This is what happens - the internallinks are
    # converted at the end.
    return key == 'Str' and imp_reflink_pattern.match(value)


def isattr(string):
    return string.startswith('{') and string.endswith('}')


def isheader(key, value):
    return (key == 'Header')


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
        if isattrfigure(key, value):
            return self.figure_replacement(key, value, format, metadata)
        elif isheader(key, value) and format in self.formats:
            return self.section_replacement(key, value, format, metadata)
        elif islabeledmath(key, value):
            return self.math_replacement(key, value, format, metadata)

    def figure_replacement(self, key, value, format, metadata):
        """Replace figures with appropriate representation and
        append info to the refdict.
        """
        image = value[0]
        attr_string = pf.stringify(value[1:])
        filename = image['c'][1][0]
        raw_caption = pf.stringify(image['c'][0])
        attrs = attr_parser.parse(attr_string)

        label = attrs['id']
        classes = attrs['classes']
        keys = [(k, v) for k, v in attrs.items() if k not in ('id', 'classes')]

        class_str = 'class="{}"'.format(' '.join(classes)) if classes else ''
        key_str = ' '.join('{}={}'.format(k, v) for k, v in keys)

        self.refdict[label] = {'type': 'figure',
                               'id': self.figure_count}

        caption = 'Figure {n}: {caption}'.format(n=self.figure_count,
                                                 caption=raw_caption)
        self.figure_count += 1

        if format == 'markdown':
            figure = markdown_figure.format(id=label,
                                            caption=caption,
                                            filename=filename)

            return pf.Para([rawmarkdown(figure)])

        elif format == 'html':
            figure = html_figure.format(id=label,
                                        classes=class_str,
                                        keys=key_str,
                                        filename=filename,
                                        alt=caption,
                                        caption=caption)
            return pf.Para([rawhtml(figure)])

        elif format == 'html5':
            figure = html5_figure.format(id=label,
                                         classes=class_str,
                                         keys=key_str,
                                         filename=filename,
                                         alt=caption,
                                         caption=caption)
            return pf.Para([rawhtml(figure)])

        elif format == 'latex':
            figure = latex_figure.format(filename=filename,
                                         caption=raw_caption,
                                         label=label)
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

    def convert_links(self, key, value, format, metadata):
        """Convert all internal links from '#blah'into format
        specified in self.replacements.
        """
        if isinternallink(key, value):
            pre, link, post = imp_reflink_pattern.match(value).groups()
            label = link[1:]  # strip leading '#'
            try:
                id = self.refdict[label]['id']
                rtype = self.refdict[label]['type']
            except KeyError:
                return None
        else:
            return None

        text = self.replacements[rtype].format(id)

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
        return [self.consume_references,
                self.convert_links]


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
