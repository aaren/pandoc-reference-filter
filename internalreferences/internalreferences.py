import re
from collections import OrderedDict

import pandocfilters as pf

from pandocattributes import PandocAttributes

from .identity import *
from .styles import *


def RawInline(format, string):
    """Overwrite pandocfilters RawInline so that html5
    and html raw output both use the html writer.
    """
    if format == 'html5':
        format = 'html'
    return pf.RawInline(format, string)


def RawBlock(format, string):
    """Overwrite pandocfilters RawBlock so that html5
    and html raw output both use the html writer.
    """
    if format == 'html5':
        format = 'html'
    return pf.RawBlock(format, string)


# define a new type for internal references [pre, label, post]
InternalRef = pf.elt('InternalRef', 3)
# and multiple references [pre, [label], post]
# https://tex.stackexchange.com/questions/15728/multiple-references-with-autoref
# https://github.com/mathjax/MathJax/issues/71
# http://docs.mathjax.org/en/latest/tex.html#automatic-equation-numbering
MultiInternalRef = pf.elt('MultiInternalRef', 3)
# define a new Figure type - an image with attributes
Figure = pf.elt('Figure', 3)  # caption, target, attrs


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

    def consume_references(self, key, value, format, metadata):
        """Find all figures, sections and math in the document
        and append reference information to the reference state.
        """
        if isFigure(key, value):
            self.consume_figure(key, value, format, metadata)
        elif isheader(key, value) and format in self.formats:
            self.consume_section(key, value, format, metadata)
        elif islabeledmath(key, value):
            self.consume_math(key, value, format, metadata)

    def replace_references(self, key, value, format, metadata):
        """Find all figures, sections and equations that can be
        referenced in the document and replace them with format
        appropriate substitutions.
        """
        if isFigure(key, value):
            return self.figure_replacement(key, value, format, metadata)
        elif isheader(key, value) and format in self.formats:
            return self.section_replacement(key, value, format, metadata)
        elif islabeledmath(key, value):
            return self.math_replacement(key, value, format, metadata)

    def consume_figure(self, key, value, format, metadata):
        """If the key, value represents a figure, append reference
        data to internal state.
        """
        _caption, (filename, target), (id, classes, kvs) = value
        if 'unnumbered' in classes:
            return
        else:
            self.figure_count += 1
            self.references[id] = {'type': 'figure',
                                   'id': self.figure_count,
                                   'label': id}

    def consume_section(self, key, value, format, metadata):
        """If the key, value represents a section, append reference
        data to internal state.
        """
        level, attr, text = value
        label, classes, kvs = attr

        if 'unnumbered' in classes:
            return
        else:
            self.increment_section_count(level)
            secn = self.format_section_count(level)
            self.references[label] = {'type': 'section',
                                      'id': secn,
                                      'label': label}

    def consume_math(self, key, value, format, metadata):
        """If the key, value represents math, append reference
        data to internal state.
        """
        self.equation_count += 1
        mathtype, math = value
        label, = re.search(r'\\label{([\w:&^]+)}', math).groups()
        self.references[label] = {'type': 'math',
                                  'id': self.equation_count,
                                  'label': label}

    def figure_replacement(self, key, value, format, metadata):
        """Replace figures with appropriate representation.

        This works with Figure, which is our special type for images
        with attributes. This allows us to set an id in the attributes.

        The other way of doing it would be to pull out a '\label{(.*)}'
        from the caption of an Image and use that to update the references.
        """
        _caption, (filename, target), attrs = value
        caption = pf.stringify(_caption)

        attr = PandocAttributes(attrs)

        if 'unnumbered' in attr.classes:
            star = '*'
            fcaption = caption
        else:
            ref = self.references[attr.id]
            star = ''
            if caption:
                fcaption = u'Figure {n}: {caption}'.format(n=ref['id'],
                                                           caption=caption)
            else:
                fcaption = u'Figure {n}'.format(n=ref['id'])

        if 'figure' not in attr.classes:
            attr.classes.insert(0, 'figure')

        if format in self.formats:
            figure = figure_styles[format].format(attr=attr,
                                                  filename=filename,
                                                  alt=fcaption,
                                                  fcaption=fcaption,
                                                  caption=caption,
                                                  star=star).encode('utf-8')

            return RawBlock(format, figure)

        else:
            alt = [pf.Str(fcaption)]
            target = (filename, '')
            image = pf.Image(alt, target)
            figure = pf.Para([image])
            return pf.Div(attr.to_pandoc(), [figure])

    def section_replacement(self, key, value, format, metadata):
        """Replace sections with appropriate representation.
        """
        level, attr, text = value
        label, classes, kvs = attr

        if 'unnumbered' in classes:
            pretext = ''
        else:
            ref = self.references[label]
            pretext = '{}: '.format(ref['id'])

        pretext = [pf.Str(pretext)]

        if format in ('html', 'html5', 'markdown'):
            return pf.Header(level, attr, pretext + text)

        elif format == 'latex':
            # have to do this to get rid of hyperref
            return pf.Header(level, attr, text)

        else:
            return pf.Header(level, attr, pretext + text)

    def math_replacement(self, key, value, format, metadata):
        """Math should not need replacing as mathjax / latex will
        take care of any references.

        http://meta.math.stackexchange.com/questions/3764/equation-and-equation-is-the-same-for-me
        """
        return

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

        if format in self.formats:
            link = link_styles[format][rtype].format(text=text,
                                                     label=label,
                                                     pre=pre,
                                                     post=post)
            return RawInline(format, link)

        else:
            link = pf.Link([pf.Str(text)], ('#' + label, ''))
            return [pf.Str(pre), link, pf.Str(post)]

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
                self.consume_references,
                self.replace_references,
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
