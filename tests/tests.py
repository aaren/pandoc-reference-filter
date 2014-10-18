import subprocess

import nose.tools as nt

import internalreferences


def test_attributes():
    attr_string = r"""{#identify .class1 .class2
    key1=blah key2="o'brien = 1" -}"""
    ref_dict = {'id': 'identify',
                'classes': ['class1', 'class2', 'unnumbered'],
                'key1': 'blah',
                'key2': '"o\'brien = 1"'
                }

    attr_dict = internalreferences.attr_parser.parse(attr_string)
    print ref_dict
    print attr_dict
    nt.assert_dict_equal(ref_dict, attr_dict)


def call_pandoc(format):
    pandoc_cmd = ('pandoc', 'spec.md',
                  '--filter', 'internalreferences.py',
                  '--mathjax',
                  '--to', format)
    p = subprocess.Popen(pandoc_cmd, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return stdout


def _test(format):
    pandoc_output = call_pandoc(format)

    ref_file = 'tests/spec.{ext}'.format(ext=format)

    with open(ref_file) as f:
        nt.assert_multi_line_equal(pandoc_output, f.read())


def test_markdown():
    _test('markdown')


def test_html():
    _test('html')


def test_html5():
    _test('html5')


def test_latex():
    _test('latex')


def test_all_formats():
    for format in ('markdown', 'latex', 'html', 'html5'):
        _test(format)


if __name__ == '__main__':
    print "Comparing pandoc output with reference output in tests/spec.format"
    test_markdown()
    test_html()
    test_html5()
    test_latex()
    print "All comparison tests passed ok!"
