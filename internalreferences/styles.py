figure_styles = {
    'latex': (u'\n'
               '\\begin{{figure}}[htbp]\n'
               '\\centering\n'
               '\\includegraphics{{{filename}}}\n'
               '\\caption{star}{{{caption}}}\n'
               '\\label{{{attr.id}}}\n'
               '\\end{{figure}}\n'),

    'html': (u'\n'
              '<div {attr.html}>\n'
              '<img src="{filename}" alt="{alt}" />'
              '<p class="caption">{fcaption}</p>\n'
              '</div>\n'),

    'html5': (u'\n'
               '<figure {attr.html}>\n'
               '<img src="{filename}" alt="{alt}" />\n'
               '<figcaption>{fcaption}</figcaption>\n'
               '</figure>\n'),

    'markdown': (u'\n'
                  '<div {attr.html}>\n'
                  '![{fcaption}]({filename})\n'
                  '\n'
                  '</div>\n')
}

# replacement text to use for in text internal links
# that refer to various types of thing, in different
# output formats
latex_link = u'{pre}\\autoref{{{label}}}{post}'
html_link = u'{pre}<a href="#{label}">{text}</a>{post}'
markdown_link = u'{pre}[{text}](#{label}){post}'

latex_math_link = u'{pre}\\autoref{{{label}}}{post}'
html_math_link = u'{pre}Equation \\eqref{{{label}}}{post}'
markdown_math_link = u'{pre}Equation $\\eqref{{{label}}}${post}'

latex_multi_link = u'\\cref{{{labels}}}{post}'

link_styles = {
    'latex': {'figure': latex_link,
              'section': latex_link,
              'math': latex_math_link},
    'html': {'figure': html_link,
             'section': html_link,
             'math': html_math_link},
    'html5': {'figure': html_link,
              'section': html_link,
              'math': html_math_link},
    'markdown': {'figure': markdown_link,
                 'section': markdown_link,
                 'math': markdown_math_link}
}
