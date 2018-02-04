0.1 Experiments with pandoc figures (ˈjuːnɪˌkəʊd!) {#sec:expt .class1 .class2 key="value"}
--------------------------------------------------

![Figure 1: a figure that can be referred to
(ˈjuːnɪˌkəʊd!)](image.png "link text"){#fig:attr .class1 .class2
key="value"}

Here is a reference to [Figure 1](#fig:attr) and here is one to
[Figure 2](#fig:attr2).

Here is reference to the section called [Section 0.1](#sec:expt).

![Figure 2: another figure that can be referred to
(ˈjuːnɪˌkəʊd!)](image.png "link text"){#fig:attr2}

![Figure 3: figure with no attr and no link text
(ˈjuːnɪˌkəʊd!)](image.png){#___fig___3}

Here is [Equation 1](#eq:silly):

+:-------------------------------------------------------------:+-----:+
| $$2 + 2 = 5$$                                                 | (1)  |
+---------------------------------------------------------------+------+

: []{#eq:silly .math}

Unnumbered Section {#unnumbered-section .unnumbered}
------------------

![no numbering here (ˈjuːnɪˌkəʊd!)](image.png "link text"){#fig:nonum
.unnumbered}

Multiple references {#multiple-references .unnumbered}
-------------------

We can refer to multiple things of the same type: [Figure 1](#fig:attr)
and [Figure 2](#fig:attr2).

Or to multiple things of mixed type: [Figure 1](#fig:attr),
[Figure 2](#fig:attr2), [Section 0.1](#sec:expt), and
[Equation 1](#eq:silly).

But if there are any missing keys, nothing will happen:
[@fig:attr; @fig:idontexist].
