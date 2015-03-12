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

latex_multi_link = u'\\cref{{{labels}}}{post}'
