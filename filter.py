import pandocfilters as pf

latex_figure = """
\\begin{{figure}}[htbp]
\\centering
\\includegraphics{{{filename}}}
\\caption{{{caption}}}
\\label{{{label}}}
\\end{{figure}}"""

html_figure = """
<figure id="{id}">
<img src="{filename}" alt="{alt}" />
<figcaption>{caption}</figcaption>
</figure>"""

markdown_figure = "![{caption}]({filename})"

latex_link = '\\autoref{{{label}}}'
html_link = '<a href="#{label}">{text}</a>'


def rawlatex(s):
    return pf.RawInline('latex', s)


def rawhtml(s):
    return pf.RawInline('html', s)


def rawmarkdown(s):
    return pf.RawInline('markdown', s)


def isfigure(key, value):
    return (key == 'Para' and len(value) == 2 and value[0]['t'] == 'Image')


def isattrfigure(key, value):
    return (isfigure(key, value) and isattr(value[1]['c']))


def isinternallink(key, value):
    return (key == 'Link' and (value[1][0]).startswith('#'))


def isattr(string):
    return string.startswith('{') and string.endswith('}')


def isheader(key, value):
    return (key == 'Header')


# we need to create a list of all of the figures and then cross
# reference them with the references in the text. The problem is
# that we need the list of figures before we can replace the text of
# the references, which we can't do with a single filter (because we
# can have the in text references appearing before the figures in
# the ast, which leaves them not knowing what number their figure
# is).

# to solve this we need to alter toJSONFilter so that it can take a
# sequence of actions to apply to the tree. The first action will
# count the figures and replace with the right html. The second
# action will put numbers in all the in text references.



# TODO: section references need to work as well.
# all internal links should be \autoref in latex output.
# section headers should have the label correctly defined - i.e. not
# as a hyperlink
# counting sections is trickier because of subsections - we can have
# e.g. 'a reference to Section 1.1.2'
# could just use some generic text, 'above' 'below'

# or 'see above' / 'Section x.y' for html / latex
# e.g.
# markdown: "we're talking about this thing ([see above](#sec:ref))"
# -> latex: "we're talking about this thing (\autoref{sec:ref})"
# -> html:  "we're talking about this thing (<a href="#sec:ref">see above</a>)
#
# this constrains language a bit, but maybe workable?

# actually, counting sections isn't that difficult. Headers are
# represented in the ast as an integer, an attribute list and a list
# of inline elements.
#
# The integer defines the level of header. All we'd need to do is
# create the list of all headers, along with their level, then
# number the headers accordingly.

# e.g.
# [1,  Section 1: La la la
#  2,  Section 1.1: more lala
#  2,  Section 1.2
#  3,  Section 1.2.1
#  3,  Section 1.2.2
#  1,  Section 2
#  2,  Section 2.1
#  1,] Section 3

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
    refdict = {}

    replacements = {'figure': 'Figure {}',
                    'section': 'Section {}'}

    formats = ('html', 'html5', 'markdown', 'latex')

    def increment_section_count(self, header_level):
        self.section_count[header_level - 1] += 1
        for i, _ in enumerate(self.section_count[header_level:]):
            self.section_count[header_level + i] = 0

    def format_section_count(self, header_level):
        return '.'.join(str(i) for i in self.section_count[:header_level])

    def consume_references(self, key, value, format, metadata):
        if isattrfigure(key, value):
            return self.figure_replacement(key, value, format, metadata)
        elif isheader(key, value) and format in self.formats:
            return self.section_replacement(key, value, format, metadata)

    def figure_replacement(self, key, value, format, metadata):
            image = value[0]
            attr = value[1]['c']
            filename = image['c'][1][0]
            caption = pf.stringify(image['c'][0])
            label = attr.strip('{}')[1:]

            if label not in self.refdict:
                self.refdict[label] = {'type': 'figure',
                                        'id': self.figure_count}
                self.figure_count += 1

            nfig = len(self.refdict)

            if format in ('markdown'):
                caption = 'Figure {n}: {caption}'.format(n=nfig, caption=caption)
                figure = markdown_figure.format(caption=caption,
                                                filename=filename)

                return pf.Para([rawmarkdown(figure)])

            elif format in ('html', 'html5'):
                caption = 'Figure {n}: {caption}'.format(n=nfig, caption=caption)
                figure = html_figure.format(id=label,
                                            filename=filename,
                                            alt=caption,
                                            caption=caption)
                return pf.Para([rawhtml(figure)])

            elif format == 'latex':
                figure = latex_figure.format(filename=filename,
                                                      caption=caption,
                                                      label=label)
                return pf.Para([rawlatex(figure)])

    def section_replacement(self, key, value, format, metadata):
        level, attr, text = value

        secn = self.format_section_count(level)
        self.increment_section_count(level)

        label = attr[0]
        self.refdict[label] = {'type': 'section',
                                'id': secn}

        pretext = '{}:'.format(secn)
        pretext = [pf.Str(pretext), pf.Space()]
        return pf.Header(level, attr, pretext + text)

    def convert_links(self, key, value, format, metadata):
        """Convert all internal links into format specified in
        self.replacements."""
        if isinternallink(key, value):
            label = value[1][0][1:]  # strip leading '#'
            try:
                id = self.refdict[label]['id']
                rtype = self.refdict[label]['type']
            except KeyError:
                return None
        else:
            return None

        text = self.replacements[rtype].format(id)

        if format in ('html', 'html5'):
            return rawhtml(html_link.format(text=text, label=label))
        elif format == 'markdown':
            return rawmarkdown(text)
        elif format == 'latex':
            return rawlatex(latex_link.format(label=label))
        else:
            return None

    @property
    def reference_filter(self):
        return [self.consume_references, self.convert_links]


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


if __name__ == '__main__':
    refmanager = ReferenceManager()
    toJSONFilter(refmanager.reference_filter)
