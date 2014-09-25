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

latex_link = '\\autoref{{{label}}}'
html_link = '<a href="{target}">{text}</a>'


def rawlatex(s):
    return pf.RawInline('latex', s)


def rawhtml(s):
    return pf.RawInline('html', s)


def isfigure(key, value):
    return (key == 'Para' and len(value) == 2 and value[0]['t'] == 'Image')


def isattrfigure(key, value):
    return (isfigure(key, value) and isattr(value[1]['c']))


def isinternallink(key, value):
    return (key == 'Link' and (value[1][0]).startswith('#'))

def isfigurelink(key, value):
    return (key == 'Link' and (value[1][0]).startswith('#fig'))

def issectionlink(key, value):
    return (key == 'Link' and (value[1][0]).startswith('#sec'))

def isattr(string):
    return string.startswith('{') and string.endswith('}')


class FigureCounter(object):
    figlist = []
    headerlist = []

figcount = FigureCounter()

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


def figure_number(key, value, format, metadata):
    """We want to number figures in the text: prepending the caption
    with 'Figure x:', replacing the reference with 'Figure x',
    putting an id on the figure  and putting a href to the figure id
    into the reference.
    """
    # make the list of figures
    if isattrfigure(key, value):
        image = value[0]
        attr = value[1]['c']
        filename = image['c'][1][0]
        caption = pf.stringify(image['c'][0])
        label = attr.strip('{}')

        # TODO: add markdown as an output

        if format in ('html', 'html5'):
            if label not in figcount.figlist:
                figcount.figlist.append(label)

            nfig = len(figcount.figlist)
            caption = 'Figure {n}: {caption}'.format(n=nfig, caption=caption)

            return pf.Para([rawhtml(html_figure.format(id=label[1:],
                                                    filename=filename,
                                                    alt=caption,
                                                    caption=caption))])
        elif format == 'latex':
            return pf.Para([rawlatex(latex_figure.format(filename=filename,
                                                      caption=caption,
                                                      label=label[1:]))])


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

class SectionCounter(object):
    count = [1, 1, 1, 1, 1, 1]
    secdict = {}

    def increment_count(self, header_level):
        self.count[header_level - 1] += 1
        for i, _ in enumerate(self.count[header_level:]):
            self.count[header_level + i] = 0

    def format_count(self, header_level):
        return '.'.join(str(i) for i in self.count[:header_level])

sectioncounter = SectionCounter()

def isheader(key, value):
    return (key == 'Header')


def section_number(key, value, format, metadata):
    if isheader(key, value) and format in ('html', 'html5'):
        level, attr, text = value

        secn = sectioncounter.format_count(level)
        sectioncounter.increment_count(level)

        label = attr[0]
        sectioncounter.secdict[label] = secn

        pretext = '{}:'.format(secn)
        pretext = [pf.Str(pretext), pf.Space()]
        return pf.Header(level, attr, pretext + text)

# we number using the format x.y.z

links = {'sec': 'Section',
         'fig': 'Figure'}


def convert_links(key, value, format, metadata):
    if isfigurelink(key, value) and format in ('html', 'html5'):
        target = value[1][0]
        try:
            fign = figcount.figlist.index(target) + 1
        except IndexError:
            return None
        text = 'Figure {}'.format(fign)
        return rawhtml(html_link.format(text=text, target=target))

    elif issectionlink(key, value) and format in ('html', 'html5'):
        target = value[1][0]
        try:
            secn = sectioncounter.secdict[target[1:]]
        except KeyError:
            return None
        text = 'Section {}'.format(secn)
        return rawhtml(html_link.format(text=text, target=target))

    elif isinternallink(key, value) and format == 'latex':
        # use autoref instead of hyperref for all internal links
        label = value[1][0][1:]  # strip leading '#'
        return rawlatex(latex_link.format(label=label))


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
    # toJSONFilter(figure_number)
    # toJSONFilter([figure_number, convert_links])
    toJSONFilter([figure_number, section_number, convert_links])
