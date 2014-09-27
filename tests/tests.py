import subprocess

import nose.tools as nt

import internalreferences


def test_attributes():
    attr_string = r"""{#identify .class1 .class2
    key1=blah key2="o'brien = 1" -}"""
    ref_dict = {'id': 'identify',
                'classes': ['class1', 'class2', 'unnumbered'],
                'kv': {'key1': 'blah', 'key2': "o'brien = 1"}
                }

    attr_dict = internalreferences.parse_attributes(attr_string)
    nt.assert_dict_equal(ref_dict, attr_dict)


def call_pandoc(format):
    pandoc_cmd = ('pandoc', 'spec.md',
                  '--filter', 'internalreferences.py',
                  '--to', format)
    p = subprocess.Popen(pandoc_cmd, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return stdout


def _test(format):
    pandoc_output = call_pandoc(format)

    ref_file = 'tests/spec.{ext}'.format(ext=format)

    with open(ref_file) as f:
        return pandoc_output, f.read()


def test_markdown():
    pandoc_output, ref = _test('markdown')
    assert(pandoc_output == ref)


def test_html():
    pandoc_output, ref = _test('html')
    assert(pandoc_output == ref)


def test_html5():
    pandoc_output, ref = _test('html5')
    assert(pandoc_output == ref)


def test_latex():
    pandoc_output, ref = _test('latex')
    assert(pandoc_output == ref)


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
