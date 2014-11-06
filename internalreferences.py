import re
from collections import OrderedDict

import pandocfilters as pf

from pandocattributes import PandocAttributes


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

latex_multi_link = '\\cref{{{labels}}}{post}'

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
    return pf.RawInline(format, string)


def isheader(key, value):
    return (key == 'Header')


def islabeledmath(key, value):
    return (key == 'Math' and re.search(r'\\label{\S*}', value[1]))


# pattern that matches #reflink
# only allow characters that we can have in latex labels
# https://tex.stackexchange.com/questions/18311/valid-label-names
# currently have to be after whitespace
# terminated by a disallowed latex character or a pipe. Use a pipe
# if you want to follow the reflink with a ':', i.e. #reflink|:
# Multiple references are possible - #one#two#three
imp_reflink_pattern = re.compile(r'([\s]?)#([\w:&^#]+)\|?(.*)')

# https://tex.stackexchange.com/questions/15728/multiple-references-with-autoref
# https://github.com/mathjax/MathJax/issues/71
# http://docs.mathjax.org/en/latest/tex.html#automatic-equation-numbering


def isinternalref(key, value):
    # This can fall over if we don't create_figures from our
    # special attr images first - it can match #id in the attrs
    return key == 'Str' and imp_reflink_pattern.match(value)

# define a new type for internal references [pre, label, post]
InternalRef = pf.elt('InternalRef', 3)
# and multiple references [pre, [label], post]
MultiInternalRef = pf.elt('MultiInternalRef', 3)


def create_pandoc_multilink(strings, refs):
    inlines = [[pf.Str(str(s))] for s in strings]
    targets = [(r, "") for r in refs]
    links = [pf.Link(inline, target)
             for inline, target in zip(inlines, targets)]

    return join_items(links)


def join_items(items, method='append'):
    """Join the list of items together in the format

    'item[0]' if len(items) == 1
    'item[0] and item[1]' if len(items) == 2
    'item[0], item[1] and item[2]' if len(items) == 3

    and so on.
    """
    out = []
    join_to_out = getattr(out, method)

    join_to_out(items[0])

    if len(items) == 1:
        return out

    for item in items[1: -1]:
        out.append(pf.Str(', '))
        join_to_out(item)

    out.append(pf.Str(' and '))
    join_to_out(items[-1])

    return out


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
    references = {}

    replacements = {'figure': 'Figure {}',
                    'section': 'Section {}',
                    'math': 'Equation {}'}

    multi_replacements = {'figure': 'Figures ',
                          'section': 'Sections ',
                          'math': 'Equations '}

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
        text whilst appending to the internal references.
        """
        if isFigure(key, value):
            return self.figure_replacement(key, value, format, metadata)
        elif isheader(key, value) and format in self.formats:
            return self.section_replacement(key, value, format, metadata)
        elif islabeledmath(key, value):
            return self.math_replacement(key, value, format, metadata)

    def figure_replacement(self, key, value, format, metadata):
        """Replace figures with appropriate representation and
        append info to the references.

        This works with Figure, which is our special type for images
        with attributes. This allows us to set an id in the attributes.

        The other way of doing it would be to pull out a '\label{(.*)}'
        from the caption of an Image and use that to update the references.
        """
        _caption, (filename, target), (id, classes, kvs) = value
        caption = pf.stringify(_caption)

        if 'unnumbered' in classes:
            star = '*'
            fcaption = caption
        else:
            self.figure_count += 1
            star = ''
            if caption:
                fcaption = 'Figure {n}: {caption}'.format(n=self.figure_count,
                                                          caption=caption)
            else:
                fcaption = 'Figure {n}'.format(n=self.figure_count)

            self.references[id] = {'type': 'figure',
                                   'id': self.figure_count,
                                   'label': id}

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
        append info to the references.
        """
        level, attr, text = value
        label, classes, kvs = attr

        if 'unnumbered' in classes:
            pretext = ''
        else:
            self.increment_section_count(level)
            secn = self.format_section_count(level)
            self.references[label] = {'type': 'section',
                                      'id': secn,
                                      'label': label}
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
        references and increment an equation count (which nothing uses
        yet).

        http://meta.math.stackexchange.com/questions/3764/equation-and-equation-is-the-same-for-me
        """
        self.equation_count += 1
        mathtype, math = value
        label, = re.search(r'\\label{([\w:&^]+)}', math).groups()
        self.references[label] = {'type': 'math',
                                  'id': self.equation_count,
                                  'label': label}
        return None

    def create_internal_refs(self, key, value, format, metadata):
        """Convert #label in the text into InternalRef, but only if the
        label is in the references.
        """
        if isinternalref(key, value):
            pre, link, post = imp_reflink_pattern.match(value).groups()
            labels = link.split('#')

            # filter out labels not in references
            labels = [label for label in labels if label in self.references]

            if len(labels) == 0:
                return None
            elif len(labels) == 1:
                return InternalRef(pre, labels[0], post)
            elif len(labels) > 1:
                return MultiInternalRef(pre, labels, post)

    def convert_internal_refs(self, key, value, format, metadata):
        """Convert all internal links from '#blah' into format
        specified in self.replacements.
        """
        if key not in ('InternalRef' 'MultiInternalRef'):
            return None

        elif key == 'MultiInternalRef':
            return self.convert_multiref(key, value, format, metadata)

        else:
            pre, label, post = value

        rtype = self.references[label]['type']
        n = self.references[label]['id']
        text = self.replacements[rtype].format(n)

        if format in self.formats or True:
            link = link_styles[format][rtype].format(text=text,
                                                     label=label,
                                                     pre=pre,
                                                     post=post)
            return RawInline(format, link)

    def convert_multiref(self, key, value, format, metadata):
        """Convert all internal links from '#blah' into format
        specified in self.replacements.
        """
        if key != 'MultiInternalRef':
            return

        pre, labels, post = value

        if format == 'latex':
            link = latex_multi_link.format(pre=pre,
                                           post=post,
                                           labels=','.join(labels))
            return RawInline('latex', link)

        else:
            D = [self.references[label] for label in labels]
            # uniquely ordered types
            types = list(OrderedDict.fromkeys(d['type'] for d in D))

            links = []

            for t in set(types):
                n = [d['id'] for d in D if d['type'] == t]
                labels = ['#' + d['label'] for d in D if d['type'] == t]
                multi_link = create_pandoc_multilink(n, labels)

                if len(labels) == 1:
                    multi_link.insert(0,
                                      pf.Str(self.replacements[t].format('')))
                else:
                    multi_link.insert(0, pf.Str(self.multi_replacements[t]))

                links.append(multi_link)

            return join_items(links, method='extend')

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


def main():
    refmanager = ReferenceManager()
    toJSONFilter(refmanager.reference_filter)


if __name__ == '__main__':
    main()
