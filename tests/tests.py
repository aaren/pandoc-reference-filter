import subprocess


def call_pandoc(format):
    pandoc_cmd = ('pandoc', 'spec.md',
                  '--filter', 'internal-references.py',
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
