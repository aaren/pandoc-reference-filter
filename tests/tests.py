import subprocess
import json

import nose.tools as nt


def call_pandoc(format):
    pandoc_cmd = ('pandoc', 'spec.md',
                  '--lua-filter', './internalreferences.lua',
                  '--mathjax',
                  '--to', format)
    p = subprocess.Popen(pandoc_cmd, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return stdout.decode()


def _test(format):
    pandoc_output = call_pandoc(format)

    ref_file = 'tests/spec.{ext}'.format(ext=format)

    with open(ref_file) as f:
        nt.assert_multi_line_equal(pandoc_output, f.read())


def test_markdown():
    _test('markdown')


def test_html():
    _test('html4')


def test_html5():
    _test('html5')


def test_latex():
    _test('latex')


def test_generic():
    test = json.loads(call_pandoc('json'))

    with open('tests/spec.json') as f:
        ref = json.load(f)

    assert test == ref


def test_all_formats():
    for format in ('markdown', 'latex', 'html', 'html5'):
        _test(format)


if __name__ == '__main__':
    print("Comparing pandoc output with reference output in tests/spec.format")
    test_markdown()
    test_html()
    test_html5()
    test_latex()
    print("All comparison tests passed ok!")
