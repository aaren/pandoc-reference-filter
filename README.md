This pandoc filter implements an internal reference manager for
pandoc, making it possible to reference images, and sections that
have attribute tags.

Supported output formats are latex, html, html5 and markdown. The
markdown output format can be used to convert
markdown-with-figure-attributes into currently valid pandoc
markdown.

For example input see the [spec] and for the output see [markdown],
[html], [html5] or [latex].

[spec]: spec.md
[markdown]: tests/spec.markdown
[html]: tests/spec.html
[html5]: tests/spec.html5
[latex]: tests/spec.latex


Usage:

```bash
pandoc spec.md --filter internal-references.py --to latex
```

Testing:

```bash
python tests/tests.py
```
