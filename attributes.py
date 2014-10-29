import re

import pandocfilters as pf


class PandocAttributes(object):
    """Parser for pandoc block attributes.

    usage:
        attrs = '#id .class1 .class2 key=value'
        parser = AttributeParser()
        parser.parse(attrs)
        >>> {'id': 'id', 'classes': ['class1', 'class2'], 'key'='value'}
    """
    spnl = ' \n'
    split_regex = r'''((?:[^{separator}"']|"[^"]*"|'[^']*')+)'''.format

    def __init__(self, attr, format='pandoc'):
        if format == 'pandoc':
            id, classes, kvs = attr
        elif format == 'markdown':
            id, classes, kvs = self.parse_markdown(attr)
        elif format == 'html':
            id, classes, kvs = self.parse_html(attr)
        elif format == 'dict':
            id, classes, kvs = self.parse_dict(attr)
        else:
            raise UserWarning('invalid format')

        self.id = id
        self.classes = classes
        self.kvs = kvs

    @classmethod
    def parse_markdown(self, attr_string):
        """Read markdown to pandoc attributes."""
        attr_string = attr_string.strip('{}')
        splitter = re.compile(self.split_regex(separator=self.spnl))
        attrs = splitter.split(attr_string)[1::2]

        try:
            id = [a[1:] for a in attrs if a.startswith('#')][0]
        except IndexError:
            id = ''

        classes = [a[1:] for a in attrs if a.startswith('.')]
        kvs = [a.split('=', 1) for a in attrs if '=' in a]
        special = ['unnumbered' for a in attrs if a == '-']
        classes.extend(special)

        return id, classes, kvs

    def parse_html(self, attr_string):
        """Read a html string to pandoc attributes."""
        splitter = re.compile(self.split_regex(separator=self.spnl))
        attrs = splitter.split(attr_string)[1::2]

        idre = re.compile(r'''id=["']?([\w ]*)['"]?''')
        clsre = re.compile(r'''class=["']?([\w ]*)['"]?''')

        id_matches = [idre.search(a) for a in attrs]
        cls_matches = [clsre.search(a) for a in attrs]

        try:
            id = [m.groups()[0] for m in id_matches if m][0]
        except IndexError:
            id = ''

        classes = [m.groups()[0] for m in cls_matches if m][0].split()

        kvs = [a.split('=', 1) for a in attrs if '=' in a]
        kvs = [(k, v) for k, v in kvs if k not in ('id', 'class')]

        special = ['unnumbered' for a in attrs if '-' in a]
        classes.extend(special)

        return id, classes, kvs

    @classmethod
    def parse_dict(self, attrd):
        """Read a dict to pandoc attributes."""
        return pf.attributes(attrd)

    def to_markdown(self):
        """Returns attributes formatted as markdown."""
        attrlist = []

        if self.id:
            attrlist.append('#' + self.id)

        for cls in self.classes:
            attrlist.append('.' + cls)

        for k, v in self.kvs:
            attrlist.append(k + '=' + v)

        return '{' + ' '.join(attrlist) + '}'

    def to_html(self):
        """Returns attributes formatted as html."""
        id, classes, kvs = self.id, self.classes, self.kvs
        id_str = 'id="{}"'.format(id) if id else ''
        class_str = 'class="{}"'.format(' '.join(classes)) if classes else ''
        key_str = ' '.join('{}={}'.format(k, v) for k, v in kvs)
        return ' '.join((id_str, class_str, key_str)).strip()

    def to_dict(self):
        """Returns attributes formatted as a dictionary."""
        d = {'id': self.id, 'classes': self.classes}
        d.update(self.kvs)
        return d

    def to_pandoc(self):
        return [self.id, self.classes, self.kvs]
