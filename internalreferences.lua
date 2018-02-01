--[[

TODO:

- For multi-refs, check to see whether refs are all of the same type, and
  handle differently as appropriate.

- Fix unnumbered tables in LaTeX

--]]

local REPLACEMENTS = {}          -- For captions and cross-references
REPLACEMENTS.figure = "Figure "  -- Note: last character here is no-break space.
REPLACEMENTS.section = "Section "
REPLACEMENTS.table = "Table "
REPLACEMENTS.math = "Equation "
local MULTI_REPLACEMENTS = {}    -- For multiple cross-references
MULTI_REPLACEMENTS.figure = "Figures "  -- Note: last character here is no-break space.
MULTI_REPLACEMENTS.section = "Sections "
MULTI_REPLACEMENTS.table = "Tables "
MULTI_REPLACEMENTS.math = "Equations "
local HTML_FIG = {}              -- Defining html[5] output for figures
HTML_FIG.html = {}
HTML_FIG.html.fig_open = '<div class="figure">'
HTML_FIG.html.fig_close = '</div>'
HTML_FIG.html.caption_open = '<p class="caption">'
HTML_FIG.html.caption_close = '</p>'
HTML_FIG.html5 = {}
HTML_FIG.html5.fig_open = '<figure>'
HTML_FIG.html5.fig_close = '</figure>'
HTML_FIG.html5.caption_open = '<figcaption>'
HTML_FIG.html5.caption_close = '</figcaption>'
local IDENTIFIERS = {}            -- List of identifiers found in doc
local FIGURE_ID = "___fig___"     -- Default figure identifier base
local FIGURE_EXISTS = false
local FIGURE_COUNT = 0
local TABLE_ID = "___tab___"      -- Default table identifier base
local TABLE_EXISTS = false
local TABLE_COUNT = 0
local MATH_ID = "___math___"      -- Default math identifier base
local MATH_COUNT = 0
local MATH_FORMULA_ALIGN = 'AlignCenter'  -- Alignment of math formula in table
local MATH_LABEL_ALIGN = 'AlignRight'  -- Alignment of math label in table
local NUMBERSECTIONS = false      -- assume user does not want numbered sections
local AUTOREFS = true             -- assume user wants autorefs.
local SECTION_COUNT = {0, 0, 0, 0, 0, 0}  -- keep track of current section number
local REFERENCES = {}             -- keep track of all refs (to create X-refs)
local SECNUMDEPTH = 4             -- highest level at which to number sections


function extendList(list, extension)
    -- Returns a list that is the concatenation of two lists.
    for _, item in pairs(extension) do
        table.insert(list, item)
    end
    return list
end

function incrementSectionCount(level)
    -- Increments SECTION_COUNT at given level
    SECTION_COUNT[level] = SECTION_COUNT[level] + 1
    for i = level + 1, SECNUMDEPTH do
        SECTION_COUNT[i] = 0
    end
end

function formatSectionCount(level)
    -- Returns formatted text for section at given level
    if level > SECNUMDEPTH then  -- Don't number higher than this.
        return ''
    end
    local text = tostring(SECTION_COUNT[1])
    for i = 2, level do
        text = text .. "." .. tostring(SECTION_COUNT[i])
    end
    return text
end

function inList(id, list)
    -- Takes an identifier, and checks to see if it is in the list of
    -- identifiers in the current document.
    for index, item in pairs(list) do
        if id == item then
            return true
        end
    end
    return false
end

function extendImageCaption(image)
    -- Takes a pandoc image and modifies its caption to add, for example,
    -- "Figure 1: ", as appropriate.
    local label = {}
    if not image.classes:find('unnumbered', 1) then
        if pandoc.utils.stringify(image.caption) == '' then
            label = {pandoc.Str(REPLACEMENTS.figure .. tostring(FIGURE_COUNT))}
        else
            label = {
                    pandoc.Str(REPLACEMENTS.figure .. tostring(FIGURE_COUNT) .. ":"),
                    pandoc.Space()
                }
        end
    end
    return label
end

function extendTableCaption(caption)
    -- Takes a pandoc image and modifies its caption to add, for example,
    -- "Figure 1: ", as appropriate.
    local label = {}
    if pandoc.utils.stringify(caption) == '' then
        label = {pandoc.Str(REPLACEMENTS.table .. tostring(TABLE_COUNT))}
    else
        label = {
                pandoc.Str(REPLACEMENTS.table .. tostring(TABLE_COUNT) .. ":"),
                pandoc.Space()
            }
    end
    return label
end

function parseAttr(text)
    -- Take string representing attributes and parse it into:
    --     (a) identifier (string)
    --     (b) classes (table of strings)
    --     (c) attributes (key-value table)
    --  Also return flag if unnumbered.
    local _, _, identifier = string.find(text, '#([A-z]%w*)')
    local classes = {}
    for match in string.gmatch(text, '%.([A-z]%w*)') do
        table.insert(classes, match)
    end
    -- Check to see if need to add "unnumbered" to classes
    local unnumbered = false
    if string.find(text, '^(-)$') or
            string.find(text, '^(-)%s') or
            string.find(text, '%s(-)%s') or
            string.find(text, '%s(-)$') then
        table.insert(classes, "unnumbered")
        unnumbered = true
    end
    local attributes = {}
    -- If `+smart` is on, pandoc will use curly quotes in the caption and hence
    -- in the attributes we're trying to process. Need to test for 5 cases: no
    -- quotes, and both single and double straight and curly quotes.
    for match in string.gmatch(text, '[A-z]%w*=[A-z]%w*') do     -- no quotes
        local key = string.match(match, '([A-z]%w*)=')
        local value = string.match(match, '=([A-z]%w*)')
        attributes[key] = value
    end
    for match in string.gmatch(text, '[A-z]%w*=“([A-z].+)”') do  --double curly
        local key = string.match(match, '([A-z]%w*)=')
        local value = string.match(match, '=“(.+)”')
        attributes[key] = value
    end
    for match in string.gmatch(text, '[A-z]%w*="([A-z].+)"') do  --double straight
        local key = string.match(match, '([A-z]%w*)=')
        local value = string.match(match, '="(.+)"')
        attributes[key] = value
    end
    for match in string.gmatch(text, "[A-z]%w*=‘([A-z].+)’") do  --single curly
        local key = string.match(match, "([A-z]%w*)=")
        local value = string.match(match, "=‘(.+)’")
        attributes[key] = value
    end
    for match in string.gmatch(text, "[A-z]%w*='([A-z].+)'") do  --single straight
        local key = string.match(match, "([A-z]%w*)=")
        local value = string.match(match, "='(.+)'")
        attributes[key] = value
    end
    return identifier, classes, attributes, unnumbered
end

function processMeta(meta)
    -- Sets local variables according to document metadata.
    if meta.numbersections == pandoc.MetaBool(true) then
        NUMBERSECTIONS = true
    end
    if meta.autoref == pandoc.MetaBool(false) then
        AUTOREFS = false
    end
    if meta.secnumdepth then
        SECNUMDEPTH = tonumber(meta.secnumdepth)
    end
end

function processHeaders(header)
    -- Adds header identifiers and reference information to local variables
    -- (for cross-references) and as appropriate modifies header content to add
    -- numbering.
    if header.classes:find('unnumbered', 1) or
            not NUMBERSECTIONS or
            header.level > SECNUMDEPTH then
        return
    end
    table.insert(IDENTIFIERS, header.identifier)
    if FORMAT == 'latex' or FORMAT == 'beamer' then
        return
    else
        incrementSectionCount(header.level)
        REFERENCES[header.identifier] = {
                type = "section",
                id = formatSectionCount(header.level),
                label = header.identifier
            }
        header.content = extendList({pandoc.Str(formatSectionCount(header.level)),
                                     pandoc.Space()},
                                    header.content)
        return header
    end
end

function processFigures(para)
    -- Checks to see if a paragraph contains a lone figure. If so, adds its
    -- identifier and cross-reference information to local variables, modifies
    -- the caption, and adds surrounding LaTeX or HTML code.
    if #para.content == 1 and para.content[1].t == "Image" then -- Para with single image
        FIGURE_EXISTS = true
        local image = para.content[1]
        if not image.classes:find('unnumbered', 1) then
            FIGURE_COUNT = FIGURE_COUNT + 1
            if image.identifier == "" then
                image.identifier = FIGURE_ID .. FIGURE_COUNT
            end
            table.insert(IDENTIFIERS, image.identifier)
            REFERENCES[image.identifier] = {
                    type = "figure",
                    id = FIGURE_COUNT,
                    label = image.identifier
                }
        end
        if FORMAT == 'latex' or FORMAT == 'beamer' then
            local shortCaption = {}
            if #image.caption > 0 then
                -- There is a caption, so check for a Span with 'shortcaption'
                -- class, and remove it from the caption.
                local caption = {}
                for _, inline in pairs(image.caption) do
                    if inline.t == 'Span' and inList('shortcaption', inline.classes) then
                        shortCaption = inline.content
                    else
                        table.insert(caption, inline)
                    end
                end
                image.caption = caption
            end
            if shortCaption == {} then
                -- If haven't already found a shortCaption, let the image's
                -- title (if any) be the shortCaption. Remove the "fig:" pandoc
                -- inserts and run through pandoc to format...
                if #image.title > 4 then
                    shortCaption = pandoc.read(string.sub(image.title, 5)).blocks[1].c
                end
            end
            local latexCaption = '\\caption['
            if image.classes:find('unnumbered', 1) then
                latexCaption = '\\caption*['
            end
            local latexFigure = {
                    pandoc.RawInline('latex', '\n\\begin{figure}[htbp]\n\\centering\n'),
                    image,
                    pandoc.RawInline('latex', latexCaption)
                }
            latexFigure = extendList(latexFigure, shortCaption)
            table.insert(latexFigure, pandoc.RawInline('latex', ']{'))
            latexFigure = extendList(latexFigure, image.caption)
            table.insert(latexFigure, pandoc.RawInline(
                    'latex',
                    '}\n\\label{' .. image.identifier .. '}\n\\end{figure}\n')
                )
            return pandoc.Para(latexFigure)
        elseif FORMAT == 'html' or FORMAT == 'html5' then
            local label = extendImageCaption(image)
            if image.title == "" or image.title == "fig:" then
                image.title = pandoc.utils.stringify(label) ..
                              pandoc.utils.stringify(image.caption)
            end
            local htmlFigure = {pandoc.RawInline(
                        'html',
                        '\n' .. HTML_FIG[FORMAT].fig_open .. '\n'
                    ),
                    image,
                    pandoc.RawInline('html', HTML_FIG[FORMAT].caption_open)
                }
            htmlFigure = extendList(htmlFigure, label)
            htmlFigure = extendList(htmlFigure, image.caption)
            table.insert(htmlFigure,
                         pandoc.RawInline(
                                          'html', HTML_FIG[FORMAT].caption_close ..
                                          '\n' ..
                                          HTML_FIG[FORMAT].fig_close .. '\n')
                    )
            return pandoc.Para(htmlFigure)
        else
            image.caption = extendList(extendImageCaption(image), image.caption)
            return pandoc.Para(image)
        end
    end
end

function processTables(theTable)
    TABLE_EXISTS = true
    local captionText = pandoc.utils.stringify(theTable.caption)
    local captionAttrs = string.match(captionText, '%s{([^}]+)}$')
    if not captionAttrs then
        captionAttrs = ''
    else  -- Remove attribute string from caption
        while true do
            local inline = table.remove(theTable.caption)
            if inline.t == 'Str' and string.find(inline.c, '^{') then
                break
            end
        end
        -- Remove final space
        if theTable.caption[#theTable.caption].t == 'Space' then
            table.remove(theTable.caption)
        end
    end
    local identifier, classes, attributes, unnumbered = parseAttr(captionAttrs)
    if unnumbered then
        if FORMAT == 'latex' or FORMAT == 'beamer' then
            -- FIXME: This doesn't work with LaTeX: I still get the table
            -- number. Possible solution would be to take the table, run it
            -- through `pandoc.read()` to get a LaTeX string, and then
            -- modify that LaTeX string to use `\\caption*{}` instead of
            -- `\\caption{}`. Finally, insert that back into the document
            -- as pandoc.RawBlock. That's pretty hackish.
            return theTable
            -- return pandoc.Div(theTable, pandoc.Attr(identifier, classes, attributes))
        else
            return theTable
        end
    end
    TABLE_COUNT = TABLE_COUNT + 1
    if identifier == nil then
        identifier = TABLE_ID .. TABLE_COUNT
    end
    table.insert(IDENTIFIERS, identifier)
    REFERENCES[identifier] = {
            type = "table",
            id = TABLE_COUNT,
            label = identifier
        }
    if FORMAT == 'latex' or FORMAT == 'beamer' then
        table.insert(
                theTable.caption,
                pandoc.RawInline('latex', '\\label{' .. identifier .. '}')
            )
    else
        theTable.caption = extendList(extendTableCaption(theTable.caption), theTable.caption)
    end
    return pandoc.Div(theTable, pandoc.Attr(identifier, classes, attributes))
    -- return theTable
end

function processMath(equation)
    -- Use codeblocks, with 'math' class, like this:
    --     ``` {.math #label}
    --     1+1=2
    --     ```
    if inList('math', equation.classes) then
        MATH_COUNT = MATH_COUNT + 1
        local a = {pandoc.Math('DisplayMath', equation.text)}
        local b = pandoc.Attr(equation.identifier, equation.classes, equation.attributes)
        if equation.identifier == nil then
            equation.identifier = MATH_ID .. MATH_COUNT
        end
        table.insert(IDENTIFIERS, equation.identifier)
        REFERENCES[equation.identifier] = {
                type = "math",
                id = MATH_COUNT,
                label = equation.identifier
            }
        if FORMAT == 'latex' or FORMAT == 'beamer' then
            return pandoc.Para({
                    pandoc.RawInline('latex', '\\begin{equation}\n'
                            .. '\\label{' .. equation.identifier .. '}\n'
                            .. equation.text .. '\n' ..
                            '\\end{equation}'),
                })
        else
            -- Return a table with a single row: equation, label. The table has
            -- a caption with an empty span encoding the attributes to make
            -- sure that information is not lost.
            return pandoc.Table(
                {pandoc.Span({pandoc.Space()}, pandoc.Attr(equation.identifier, equation.classes, equation.attributes))},
                {MATH_FORMULA_ALIGN, MATH_LABEL_ALIGN},
                {.9,.1},
                {},
                {
                    {{pandoc.Para({pandoc.Math('DisplayMath', equation.text)})}, 
                    {pandoc.Para({pandoc.Str('(' .. MATH_COUNT .. ')')})}}
                })
        end
    end
end

function convertSingleRef(citation)
    -- Returns a list of pandoc-formatted inlines representing a single citation.
    local link = citation.prefix
    if pandoc.utils.stringify(citation.prefix) ~= '' then
        table.insert(link, pandoc.Space())
    end
    if FORMAT == 'latex' or FORMAT == 'beamer' then
        if AUTOREFS then
            table.insert(link,
                    pandoc.RawInline('latex', '\\cref{' .. citation.id .. '}')
                )
        else
            table.insert(link,
                    pandoc.RawInline('latex', '\\ref{' .. citation.id .. '}')
                )
        end
        link:extend(citation.suffix)
        return link
    else
        local linkText = REFERENCES[citation.id].id
        if AUTOREFS then
            linkText = REPLACEMENTS[REFERENCES[citation.id].type] .. linkText
        end
        table.insert(link, pandoc.Link(pandoc.Str(linkText), '#' .. citation.id))
        -- link:extend(citation.suffix)
        link = extendList(link, citation.suffix)
        return link
    end
end

function joinInlines(items)
    -- Takes list of pandoc-formatted inlines and joins them with "," and " and ".
    if #items == 0 then
        return {}
    elseif #items == 1 then
        return item[1]
    elseif #items == 2 then
        return {items[1], pandoc.Space(), pandoc.Str('and'), pandoc.Space(), items[2]}
    else
        local list = {items[1]}
        for i = 2, #items - 1 do
            extendList(list, {pandoc.Str(','), pandoc.Space(), items[i]})
        end
        extendList(list, {pandoc.Str(','), pandoc.Space(), pandoc.Str('and'), pandoc.Space(), items[#items]})
        return list
    end
end

function convertMultiref(citations)
    -- Takes a list of citations and returns a list of pandoc-formatted inlines
    -- representing multi-citation (including links).
    -- First create a list of links
    local links = {}
    for _, citation in pairs(citations) do
        if FORMAT == 'latex' or FORMAT == 'beamer' then
            table.insert(links, citation.id)
        else
            -- FIXME: Perhaps should check if links are all of the same type, and
            -- if so use MULTI_REPLACEMENTS instead of convertSingleRef().
            local linkText = REFERENCES[citation.id].id
            if AUTOREFS then
                linkText = REPLACEMENTS[REFERENCES[citation.id].type] .. linkText
            end
            table.insert(links,
                    pandoc.Link(pandoc.Str(linkText), '#' .. citation.id)
                )
        end
    end
    -- Now format the links in that list.
    if FORMAT == 'latex' or FORMAT == 'beamer' then
        if AUTOREFS then
            return pandoc.RawInline('latex', '\\cref{' .. table.concat(links, ',') .. '}')
        else
            local refs = {}
            for _, ref in pairs(links) do
                table.insert(refs, pandoc.RawInline('latex', '\\ref{' .. ref .. '}'))
            end
            return joinInlines(refs)
        end
    else
        return joinInlines(links)
    end
end

function processCitations(cite)
    -- Takes a pandoc citation, and, if it references an internal
    -- (non-bibliographic) item, converts it to an appropriately formatted
    -- cross-reference.
    if #cite.citations == 1 then
        if inList(cite.citations[1].id, IDENTIFIERS) then
            return convertSingleRef(cite.citations[1])
        else
            return
        end
    else
        -- Note: checking to ensure that *all* of the citations in a
        -- multicitation are in the reference list. If not, the citation is
        -- bibliographic, and we want pandoc to handle it, so just return
        -- unmodified.
        for index, citation in pairs(cite.citations) do
            if not inList(citation.id, IDENTIFIERS) then
                return
            end
        end
        return convertMultiref(cite.citations)
    end
end

function updateMeta(meta)
    -- Modify metadata to reflect presence of tables or figures.
    if FORMAT == 'latex' or FORMAT == 'beamer' then
        if FIGURE_EXISTS then
            meta.graphics = pandoc.MetaBool(true)
        end
        if TABLE_EXISTS then
            meta.tables = pandoc.MetaBool(true)
        end
        return meta
    end
end

return {
    {Meta      = processMeta},       -- first to capture metadata in local variables
    {Header    = processHeaders},    -- before Cite
    {Para      = processFigures},    -- before Cite
    {Table     = processTables},     -- before Cite
    {CodeBlock = processMath},       -- before Cite
    {Cite      = processCitations},  -- next-to-last
    {Meta      = updateMeta},        -- last
}
