---
title: Pandoc Reference Filter Test
author:
date: February 04, 2018
abstract:
numbersections: true
---

## Experiments with pandoc figures (ˈjuːnɪˌkəʊd!) {#sec:expt .class1 .class2
key=value}

![a figure that can be referred to (ˈjuːnɪˌkəʊd!)](image.png "link
text"){#fig:attr .class1 .class2 key=value}

Here is a reference to [@fig:attr] and here is one to [@fig:attr2].

Here is reference to the section called @sec:expt.

![another figure that can be referred to (ˈjuːnɪˌkəʊd!)](image.png "link
text"){#fig:attr2}

![figure with no attr and no link text (ˈjuːnɪˌkəʊd!)](image.png)

Here is @eq:silly:

``` {#eq:silly .math}
2 + 2 = 5
```

## Unnumbered Section {-}

![no numbering here (ˈjuːnɪˌkəʊd!)](image.png "link text"){#fig:nonum -}


## Multiple references {-}

We can refer to multiple things of the same type: [@fig:attr; @fig:attr2].

Or to multiple things of mixed type: [@fig:attr; @fig:attr2; @sec:expt;
@eq:silly].

But if there are any missing keys, nothing will happen: [@fig:attr;
@fig:idontexist].

## Tables

| 1 | 2 |
|---|---|
| a | b |

:   This is my caption. {#mytable}

| 1 | 2 |
|---|---|
| a | b |

:   Another caption. {-}

Does this work? (See @mytable\.)
