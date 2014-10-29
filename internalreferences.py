import re

import pandocfilters as pf

from attributes import PandocAttributes


figure_styles = {'latex': ('\n'
                           '\\begin{{figure}}[htbp]\n'
                           '\\centering\n'
                           '\\includegraphics{{{filename}}}\n'
                           '\\caption{star}{{{caption}}}\n'
                           '\\label{{{id}}}\n'
                           '\\end{{figure}}\n'),

                 'html': ('\n'
                          '<div {attrs}>\n'
                          '<img src="{filename}" alt="{alt}" />'
                          '<p class="caption">{fcaption}</p>\n'
                          '</div>\n'),

                 'html5': ('\n'
                           '<figure {attrs}>\n'
                           '<img src="{filename}" alt="{alt}" />\n'
                           '<figcaption>{fcaption}</figcaption>\n'
                           '</figure>'),

                 'markdown': ('\n'
                              '<div {attrs}>\n'
                              '![{fcaption}]({filename})\n'
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


def RawInline(format, string):
    """Overwrite pandocfilters RawInline so that html5
    and html raw output both use the html writer.
    """
    if format == 'html5':
        format = 'html'
        # pass
    return pf.RawInline(format, string)


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


def isdivfigure(key, value):
    """Matches images contained in a Div with 'figure' as a class."""
    return (key == 'Div' and 'figure' in value[0][1])


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
        attr = PandocAttributes(pf.stringify(value[1:]), 'markdown')
        caption, target = image['c']
        return Figure(caption, target, attr.to_pandoc())

    elif isdivfigure(key, value):
        # use the first image inside
        attr, blocks = value
        images = [b['c'][0] for b in blocks if b['c'][0]['t'] == 'Image']
        image = images[0]
        caption, target = image['c']
        return Figure(caption, target, attr)

    else:
        return None


class ReferenceManager(object):
    """Internal reference manager.

    Stores all referencable objects in the document, with a label
    and a type, then allows us to look up the object and type using
    a label.

    This means that we can determine the appropriate replacement
    text of any given internal reference (no need for e.g. 'fig:' at
    the start of labels).
    """
    section_count = [0, 0, 0, 0, 0, 0]
    figure_count = 0
    equation_count = 0
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

    def consume_and_replace_references(self, key, value, format, metadata):
        """Find all figures, sections and equations that can be
        referenced in the document and replace them with appropriate
        text whilst appending to the internal refdict.
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
        caption = pf.stringify(_caption)

        if 'unnumbered' in classes:
            star = '*'
            fcaption = caption
        else:
            self.figure_count += 1
            star = ''
            fcaption = 'Figure {n}: {caption}'.format(n=self.figure_count,
                                                      caption=caption)
            self.refdict[id] = {'type': 'figure',
                                'id': self.figure_count}

        if 'figure' not in classes:
            classes.insert(0, 'figure')

        attr = PandocAttributes((id, classes, kvs))
        attrs = attr.to_html()

        if format in self.formats:
            figure = figure_styles[format].format(attrs=attrs,
                                                  id=id,
                                                  filename=filename,
                                                  alt=fcaption,
                                                  fcaption=fcaption,
                                                  caption=caption,
                                                  star=star)
            return pf.Para([RawInline(format, figure)])

    def section_replacement(self, key, value, format, metadata):
        """Replace sections with appropriate representation and
        append info to the refdict.
        """
        level, attr, text = value
        label, classes, kvs = attr

        if 'unnumbered' in classes:
            pretext = ''
        else:
            self.increment_section_count(level)
            secn = self.format_section_count(level)
            self.refdict[label] = {'type': 'section',
                                   'id': secn}
            pretext = '{}: '.format(secn)

        pretext = [pf.Str(pretext)]

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
        self.equation_count += 1
        mathtype, math = value
        label, = re.search(r'\\label{([\w:&^]+)}', math).groups()
        self.refdict[label] = {'type': 'math',
                               'id': self.equation_count}
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

        if format in self.formats or True:
            link = link_styles[format][rtype].format(text=text,
                                                     label=label,
                                                     pre=pre,
                                                     post=post)
            return RawInline(format, link)

    @property
    def reference_filter(self):
        return [create_figures,
                self.consume_and_replace_references,
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
