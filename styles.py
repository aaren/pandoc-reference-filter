figure_styles = {
    'latex': ('\n'
              '\\begin{{figure}}[htbp]\n'
              '\\centering\n'
              '\\includegraphics{{{filename}}}\n'
              '\\caption{star}{{{caption}}}\n'
              '\\label{{{attr.id}}}\n'
              '\\end{{figure}}\n'),

    'html': ('\n'
             '<div {attr.html}>\n'
             '<img src="{filename}" alt="{alt}" />'
             '<p class="caption">{fcaption}</p>\n'
             '</div>\n'),

    'html5': ('\n'
              '<figure {attr.html}>\n'
              '<img src="{filename}" alt="{alt}" />\n'
              '<figcaption>{fcaption}</figcaption>\n'
              '</figure>\n'),

    'markdown': ('\n'
                 '<div {attr.html}>\n'
                 '![{fcaption}]({filename})\n'
                 '\n'
                 '</div>\n')
}

# replacement text to use for in text internal links
# that refer to various types of thing, in different
# output formats
latex_link = '{pre}\\autoref{{{label}}}{post}'
html_link = '{pre}<a href="#{label}">{text}</a>{post}'
markdown_link = '{pre}[{text}](#{label}){post}'

latex_math_link = '{pre}\\autoref{{{label}}}{post}'
html_math_link = '{pre}Equation \\eqref{{{label}}}{post}'
markdown_math_link = '{pre}Equation $\\eqref{{{label}}}${post}'

latex_multi_link = '\\cref{{{labels}}}{post}'

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
