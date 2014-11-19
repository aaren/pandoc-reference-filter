import re

import pandocfilters as pf

# pattern that matches #reflink
# only allow characters that we can have in latex labels
# https://tex.stackexchange.com/questions/18311/valid-label-names
# currently have to be after whitespace
# terminated by a disallowed latex character or a pipe. Use a pipe
# if you want to follow the reflink with a ':', i.e. #reflink|:
# Multiple references are possible - #one#two#three
imp_reflink_pattern = re.compile(r'([\s]?)#([\w:&^#]+)\|?(.*)')


def isheader(key, value):
    return (key == 'Header')


def islabeledmath(key, value):
    return (key == 'Math' and re.search(r'\\label{\S*}', value[1]))


def isinternalref(key, value):
    # This can fall over if we don't create_figures from our
    # special attr images first - it can match #id in the attrs
    return key == 'Str' and imp_reflink_pattern.match(value)


def isattr(string):
    return string.startswith('{') and string.endswith('}')


def isfigure(key, value):
    return (key == 'Para' and len(value) == 2 and value[0]['t'] == 'Image')


def isattrfigure(key, value):
    return (key == 'Para'
            and value[0]['t'] == 'Image'
            and isattr(pf.stringify(value[1:])))


def isdivfigure(key, value):
    """Matches images contained in a Div with 'figure' as a class."""
    return (key == 'Div' and 'figure' in value[0][1])


def isFigure(key, value):
    return key == 'Figure'
