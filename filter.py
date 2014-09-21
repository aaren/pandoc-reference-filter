import pandocfilters as pf

latex_figure = """
\\begin{{figure}}[htbp]
\\label{{{label}}}
\\centering
\\includegraphics{{{filename}}}
\\caption{{{caption}}}
\\end{{figure}}"""

# latex_figure = " \\begin{{figure}}[htbp] \\label{{{label}}} \\centering \\includegraphics{{{filename}}} \\caption{{{caption}}} \\end{{figure}}"



def latex(s):
    return pf.RawInline('latex', s)

def figure(key, value, format, metadata):
    # a figure is created when an image (which is an inline element)
    # is the only element in a paragraph. If we have a image and
    # some attr defined with {}, then the length of the paragraph
    # list will be 2.
    if (key == 'Para' and len(value) == 2 and value[0]['t'] == 'Image'
            and value[1]['c'].startswith('{#') and value[1]['c'].endswith('}')):
            # and format == 'latex'):
        filename = value[0]['c'][1][0]
        caption = pf.stringify(value[0]['c'][0])
        label = value[1]['c'].strip('{}')
        return pf.Para([latex(latex_figure.format(filename=filename,
                                                  caption=caption,
                                                  label=label))])

# latex_fig = latex_figure.format(label=1, filename=2, caption=3)
# print latex_fig
# print latex(latex_fig)
# print pf.Str(latex(latex_fig))
# exit()

if __name__ == '__main__':
    pf.toJSONFilter(figure)
