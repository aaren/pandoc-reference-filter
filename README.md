This pandoc filter implements an internal reference manager for
pandoc, making it possible to reference images and sections that
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


### Usage:

```bash
pandoc spec.md --filter internal-references.py --to latex
```

alternately you can install it and use the command line link:

```bash
python setup.py install
pandoc spec.md --filter internal-references --to latex
```


Requires [pandocfilters] and [pandoc].

[pandocfilters]: https://pypi.python.org/pypi/pandocfilters
[pandoc]: http://johnmacfarlane.net/pandoc/


### How it works:

In order to manage references we need to maintain some internal
state that tracks the objects that can be referenced in the
document. This is implemented with the `ReferenceManager`.

`pandocfilters` contains a function `toJSONFilter` that passes a
given function over the entire document syntax tree and interfaces
with pandoc via stdin/stdout.

However, we need to walk the document tree twice, once to capture
all of the objects (figures, sections, whatever) and again to change
all of the internal links to the appropriate output. This requires a
modified `toJSONFilter` that accepts a list of functions to pass the
tree through sequentially.

It is easy to determine the type of a reference object as we go
along (whether figure, section or whatever) on the first pass and we
can use this information to let us choose the right text for
internal links on the second pass. This allows us to avoid being
constrained to ids like '#fig:somefigure' to indicate a figure.


### TODO:

- [ ] allow switching off figure / section text replacement (perhaps
  using document metadata as the switch)


### Contributing:

Very welcome. Make sure you add appropriate tests and use verbose
commit messages and pull requests.  Explain what you are trying to
do in English so that I don't have to work it out through the code.
