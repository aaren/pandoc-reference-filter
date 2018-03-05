#!/bin/bash
pandoc spec.md --lua-filter ./internalreferences.lua -o tests/spec.markdown -t markdown
pandoc spec.md --lua-filter ./internalreferences.lua -o tests/spec.latex -t latex
pandoc spec.md --lua-filter ./internalreferences.lua -o tests/spec.html4 -t html4
pandoc spec.md --lua-filter ./internalreferences.lua -o tests/spec.html5 -t html5
