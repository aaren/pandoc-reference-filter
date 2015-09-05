#!/usr/bin/env python
import re
from collections import OrderedDict
from subprocess import Popen, PIPE

import pandocfilters as pf

from pandocattributes import PandocAttributes


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


def isheader(key, value):
    return (key == 'Header')


math_label = r'\\label{(.*?)}'

def islabeledmath(key, value):
    return (key == 'Math' and re.search(math_label, value[1]))


def isattr(string):
    return string.startswith('{') and string.endswith('}')


# define a new Figure and Table types -- with attributes
Figure = pf.elt('Figure', 3)  # caption, target, attrs
TableAttrs = pf.elt('TableAttrs', 6) # caption, alignment, size, headers, rows, attrs


def isfigure(key, value):
    try:
        return (key == 'Para' and len(value) == 2 and value[0]['t'] == 'Image')
    except IndexError: return False


def isattrfigure(key, value):
    try:
        return (key == 'Para'
                and value[0]['t'] == 'Image'
                and isattr(pf.stringify(value[1:])))
    except IndexError: return False


def isdivfigure(key, value):
    """Matches images contained in a Div with 'figure' as a class."""
    try: 
        return (key == 'Div' and 'figure' in value[0][1])
    except IndexError: return False


def isFigure(key, value):
    return key == 'Figure'


def isTableAttrs(key, value):
    return key == 'TableAttrs'


def tableattrCaption(captionList):
    orig = captionList
    caption = []
    attrs = ''
    try:
        if not captionList[-1]['c'].endswith('}'):
            return captionList, None
    except IndexError: return captionList, None
    attrs += captionList.pop()['c']
    if attrs.startswith('{'): return captionList[:-1], attrs.strip('{}')
    while True:
        try:
            a = captionList.pop()
        except IndexError: break
        if a['t'] == 'Space': attrs = ' ' + attrs
        elif a['t'] == 'Str':
             attrs = a['c'] + attrs
             if a['c'].startswith('{'): break
        else: return captionList, None #Improper syntax
    if attrs:
        return captionList, attrs.strip('{}')
    else: return orig, None


def create_pandoc_multilink(strings, refs):
    inlines = [[pf.Str(str(s))] for s in strings]
    targets = [(r, "") for r in refs]
    links = [pf.Link(inline, target)
             for inline, target in zip(inlines, targets)]

    return join_items(links)


def create_latex_multilink(labels):
    links = ['\\ref{{{label}}}'.format(label=label) for label in labels]
    return join_items(links, call=str)


def join_items(items, method='append', call=pf.Str):
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
        out.append(call(', '))
        join_to_out(item)

    out.append(call(' and '))
    join_to_out(items[-1])

    return out


def create_figures(key, value, format, metadata):
    """Convert Images with attributes to Figures.

    Images are [caption, (filename, title)].

    Figures are [caption, (filename, title), attrs].

    This isn't a supported pandoc type, we just use it internally.
    """
    if isattrfigure(key, value):
        image = value[0] # E.g.: {"t":"Image","c":[[{"t":"Str","c":"CAPTION"}],["FIGURE.JPG","TITLE"]]}
        attr = PandocAttributes(pf.stringify(value[1:]), 'markdown') # E.g.: {"t":"Str","c":"{#REFERENCE}"}
        caption, target = image['c'] # E.g.: caption = [{"t":"Str","c":"CAPTION"}]; target = ["FIGURE.JPG","TITLE"]
        return Figure(caption, target, attr.to_pandoc()) # E.g.: {"t":"Figure", "c":[[{"t":"Str","c":"CAPTION"}],["FIGURE.JPG","TITLE"],"{#REFERENCE}"]}

    elif isdivfigure(key, value):
        # use the first image inside
        attr, blocks = value
        images = [b['c'][0] for b in blocks if b['c'][0]['t'] == 'Image']
        image = images[0]
        caption, target = image['c']
        return Figure(caption, target, attr)

    else:
        return None

def toFormat(string, fromThis, toThis):
    # Process string through pandoc to get formatted string. Is there a better way?
    p1 = Popen(['echo'] + string.split(), stdout=PIPE)
    p2 = Popen(['pandoc', '-f', fromThis, '-t', toThis], stdin=p1.stdout, stdout=PIPE)
    p1.stdout.close()
    return p2.communicate()[0].strip('\n')

def latex_figure(attr, filename, caption, alt):
    beginText = (u'\n'
               '\\begin{{figure}}[htbp]\n'
               '\\centering\n'
               '\\includegraphics{{{filename}}}\n'.format(
                                           filename=filename
                                           ).encode('utf-8'))
    endText = (u'}}\n'
               '\\label{{{attr.id}}}\n'
               '\\end{{figure}}\n'.format(attr=attr))

    if 'unnumbered' in attr.classes: star = True
    else: star = False
    
    if alt and not star:
        shortCaption = toFormat(alt, 'markdown', 'latex')
        beginText += '\\caption['
        latexFigure = [RawInline('latex', beginText)]
        latexFigure += [RawInline('latex', shortCaption + ']{')] 
    
    else: # No short caption
        if star: beginText += '\\caption*{'
        else: beginText += '\\caption{'
        latexFigure = [RawInline('latex', beginText)]

    latexFigure += caption
    latexFigure += [RawInline('latex', endText)]
    return pf.Para(latexFigure)

def html_figure(attr, filename, fcaption, alt):
    beginText = (u'\n'
                  '<div {attr.html}>\n'
                  '<img src="{filename}" alt="{alt}" />\n'
                  '<p class="caption">').format(attr=attr,
                                                filename=filename,
                                                alt=alt)
    endText = (u'</p>\n'
                '</div>\n')
    htmlFigure = [RawInline('html', beginText)]
    htmlFigure += fcaption
    htmlFigure += [RawInline('html', endText)]
    return pf.Plain(htmlFigure)

def html5_figure(attr, filename, fcaption, alt):
    beginText = (u'\n'
                   '<figure {attr.html}>\n'
                   '<img src="{filename}" alt="{alt}" />\n'
                   '<figcaption>').format(attr=attr,
                                          filename=filename,
                                          alt=alt)
    endText = u'</figcaption>\n</figure>\n'
    htmlFigure = [RawInline('html5', beginText)]
    htmlFigure += fcaption
    htmlFigure += [RawInline('html5', endText)]
    return pf.Plain(htmlFigure)

def markdown_figure(attr, filename, fcaption, alt):
    beginText = u'<div {attr.html}>'.format(attr=attr)
    endText = u'</div>'
    markdownFigure = [pf.Para([pf.RawInline('html', beginText)])]
    markdownFigure += [pf.Para([pf.Image(fcaption, (filename,alt))])]
    markdownFigure += [pf.Para([pf.RawInline('html', endText)])]
    return markdownFigure


def create_tableattrs(key, value, format, metadata):
    """Convert Tables with attributes to TableAttr.
    
    Tables are [caption, alignment, size, headers, rows]
    
    TableAttrs are [caption, alignment, size, headers, rows, attrs]
    
    Like Figures, this isn't supported pandoc type but only used
    internally.
    """
    if key == 'Table':
        captionList, alignment, size, headers, rows = value
        caption, attrs = tableattrCaption(captionList)
        if attrs:
            attrs = PandocAttributes(attrs, 'markdown')
            return TableAttrs(caption, alignment, size, headers, rows, attrs.to_pandoc())
    else:
        return None


def latex_table(caption, alignment, size, headers, rows, id, classes, kvs):
    """Convert to LaTeX table.
    
    FIXME: This is a complete hack. I construct a complete json representation
    of the LaTeX table, send that string to pandoc to produce a LaTeX snippet,
    modify the LaTeX snippet to alter the caption and insert a label, and 
    finally insert the LaTeX snippet into the document as a RawBlock. Surely
    there's a better way.
    """
    jsonCaption = [{'unMeta':{}}] + [[pf.Para(caption)]]
    jsonCaption = str(jsonCaption).replace("u'", "'").replace("'", '"')
    latexCaption = toFormat(jsonCaption, 'json', 'latex').replace('\\', '\\\\')
    jsonTableContents = [[pf.Str('REPLACE')], alignment, size, headers, rows]
    jsonTable = [{'unMeta':{}}, [{"t":"Table", "c":jsonTableContents}]]
    jsonTable = str(jsonTable).replace("u'", "'").replace("'", '"')
    latexTable = toFormat(jsonTable, 'json', 'latex')
    latexTable = re.sub(r'\\caption\{REPLACE\}', '\\caption{' + latexCaption + '}', latexTable, 1)
    latexTable = re.sub(r'\\end\{longtable\}', '\\label{' + id + '}\n\\end{longtable}', latexTable, 1)
    return RawBlock('latex', latexTable)


class ReferenceManager(object):
    """Internal reference manager.

    Stores all referencable objects in the document, with a label
    and a type, then allows us to look up the object and type using
    a label.

    This means that we can determine the appropriate replacement
    text of any given internal reference (no need for e.g. 'fig:' at
    the start of labels).
    """

    latex_multi_autolink = u'\\cref{{{labels}}}{post}'

    section_count = [0, 0, 0, 0, 0, 0]
    figure_count = 0
    fig_replacement_count = 0
    auto_fig_id = '___fig___[{}]'.format
    equation_count = 0
    table_count = 0
    table_replacement_count = 0
    auto_table_id = '___tab___[{}]'.format
    references = {}

    formats = ('html', 'html5', 'markdown', 'latex')

    def __init__(self, autoref=True):
        if autoref:
            self.replacements = {'figure': 'Figure {}',
                                 'section': 'Section {}',
                                 'table': 'Table {}',
                                 'math': 'Equation {}'}

            self.multi_replacements = {'figure': 'Figures ',
                                       'section': 'Sections ',
                                       'table': 'Tables ',
                                       'math': 'Equations '}
        elif not autoref:
            self.replacements = {'figure': '{}',
                                 'section': '{}',
                                 'table': '{}',
                                 'math': '{}'}

            self.multi_replacements = {'figure': '',
                                       'section': '',
                                       'table': '',
                                       'math': ''}

        self.autoref = autoref

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
        elif isTableAttrs(key, value):
            self.consume_tableattr(key, value, format, metadata)
        elif isheader(key, value):
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
        elif isTableAttrs(key, value):
            return self.tableattrs_replacement(key, value, format, metadata)
        elif isheader(key, value):
            return self.section_replacement(key, value, format, metadata)
        elif islabeledmath(key, value):
            return self.math_replacement(key, value, format, metadata)

    def consume_figure(self, key, value, format, metadata):
        """If the key, value represents a figure, append reference
        data to internal state.
        """
        _caption, (filename, alt), (id, classes, kvs) = value
        if 'unnumbered' in classes:
            return
        else:
            self.figure_count += 1
            id = id or self.auto_fig_id(self.figure_count)
            self.references[id] = {'type': 'figure',
                                   'id': self.figure_count,
                                   'label': id}
    
    def consume_tableattr(self, key, value, format, metadata):
        caption, alignment, size, headers, rows, (id, classes, kvs) = value
        if 'unnumbered' in classes:
            return
        else:
            self.table_count += 1
            id = id or self.auto_table_id(self.table_count)
            self.references[id] = {'type': 'table',
                                   'id': self.table_count,
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
        label, = re.search(math_label, math).groups()
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
        caption, (filename, alt), attrs = value

        attr = PandocAttributes(attrs)

        if 'unnumbered' in attr.classes:
            fcaption = caption
        else:
            self.fig_replacement_count += 1
            if not attr.id:
                attr.id = self.auto_fig_id(self.fig_replacement_count)

            ref = self.references[attr.id]
            if caption:
                fcaption = [pf.Str('Figure'), pf.Space(), pf.Str(str(ref['id'])+ ':'), pf.Space()] + caption
            else:
                fcaption = [pf.Str('Figure'), pf.Space(), pf.Str(str(ref['id']))]

        if 'figure' not in attr.classes:
            attr.classes.insert(0, 'figure')
        
        if format == 'latex': return latex_figure(attr, filename, caption, alt)
        elif format == 'html': return html_figure(attr, filename, fcaption, alt)
        elif format == 'html5': return html5_figure(attr, filename, fcaption, alt)
        elif format == 'markdown': return markdown_figure(attr, filename, fcaption, alt)
        else:
            image = pf.Image(fcaption, [filename, 'fig:'])
            return pf.Para([image])
    
    def tableattrs_replacement(self, key, value, format, metadata):
        """Replace TableAttrs with appropriate representation.
        
        TableAttrs is our special type for tables with attributes,
        allowing us to set an id in the attributes.
        """
        caption, alignment, size, headers, rows, (id, classes, kvs) = value
        
        if 'unnumbered' in classes:
            fcaption = caption
        else:
            self.table_replacement_count += 1
            if not id:
                id = self.auto_table_id(self.table_replacement_count)
            
            ref = self.references[id]
            if caption:
                fcaption = [pf.Str('Table'), pf.Space(), pf.Str(str(ref['id']) + ':'), pf.Space()] + caption
            else:
                fcaption = [pf.Str('Table'), pf.Space(), pf.Str(str(ref['id']))]
        
        if format == 'latex': 
            return latex_table(caption, alignment, size, headers, rows, id, classes, kvs)
        else:
            return pf.Div([id, classes, kvs], [pf.Table(fcaption, alignment, size, headers, rows)])

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
        """Create our own links to equations instead of relying on
        mathjax.

        http://meta.math.stackexchange.com/questions/3764/equation-and-equation-is-the-same-for-me
        """
        mathtype, math = value
        label = re.findall(math_label, math)[-1]

        attr = PandocAttributes()
        attr.id = '#' + label

        if format == 'latex':
            return pf.Math(mathtype, math)

        else:
            return pf.Span(attr.to_pandoc(), [pf.Math(mathtype, math)])

    def convert_internal_refs(self, key, value, format, metadata):
        """Convert all internal links from '#blah' into format
        specified in self.replacements.
        """
        if key != 'Cite':
            return None

        citations, inlines = value

        if len(citations) > 1:
            '''
            Note: Need to check that *all* of the citations in a
            multicitation are in the reference list. If not, the citation
            is bibliographic, and we want LaTeX to handle it, so just
            return unmodified.
            '''
            for citation in citations:
                if citation['citationId'] not in self.references: return
            return self.convert_multiref(key, value, format, metadata)

        else:
            citation = citations[0]

        prefix = citation['citationPrefix'] + [pf.Space()]
        suffix = citation['citationSuffix']
        

        label = citation['citationId']

        if label not in self.references:
            return

        rtype = self.references[label]['type']
        n = self.references[label]['id']
        text = self.replacements[rtype].format(n)

        if format == 'latex' and self.autoref:
            link = pf.RawInline('latex', '\\autoref{{{label}}}'.format(label=label))
            return prefix + [link] + suffix

        elif format == 'latex' and not self.autoref:
            link = pf.RawInline('latex', '\\ref{{{label}}}'.format(label=label))
            return prefix + [link] + suffix

        else:
            link = pf.Link([pf.Str(text)], ('#' + label, ''))
            return prefix + [link] + suffix

    def convert_multiref(self, key, value, format, metadata):
        """Convert all internal links from '#blah' into format
        specified in self.replacements.
        """
        citations, inlines = value

        labels = [citation['citationId'] for citation in citations]

        if format == 'latex' and self.autoref:
            link = self.latex_multi_autolink.format(pre='',
                                                    post='',
                                                    labels=','.join(labels))
            return RawInline('latex', link)

        elif format == 'latex' and not self.autoref:
            link = ''.join(create_latex_multilink(labels))
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
                create_tableattrs,
                self.consume_references,
                self.replace_references,
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
    doc = pf.json.loads(pf.sys.stdin.read())
    if len(pf.sys.argv) > 1:
        format = pf.sys.argv[1]
    else:
        format = ""

    metadata = doc[0]['unMeta']
    args = {k: v['c'] for k, v in metadata.items()}
    autoref = args.get('autoref', True)

    refmanager = ReferenceManager(autoref=autoref)

    altered = doc
    for action in refmanager.reference_filter:
        altered = pf.walk(altered, action, format, metadata)

    pf.json.dump(altered, pf.sys.stdout)


if __name__ == '__main__':
    main()
