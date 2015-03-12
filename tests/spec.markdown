0.1: Experiments with pandoc figures (ˈjuːnɪˌkəʊd!) {#sec:expt .class1 .class2 key="value"}
---------------------------------------------------


<div id="fig:attr" class="figure class1 class2" key=value>
![Figure 1: a figure that can be referred to (ˈjuːnɪˌkəʊd!)](image.png)

</div>

Here is a reference to [Figure 1](#fig:attr) and here is one to
[Figure 2](#fig:attr2).

Here is reference to the section called [Section 0.1](#sec:expt).


<div id="fig:attr2" class="figure">
![Figure 2: another figure that can be referred to (ˈjuːnɪˌkəʊd!)](image.png)

</div>

![figure with no attr (ˈjuːnɪˌkəʊd!)](image.png)

Here is [Equation 1](#eq:silly):

<span id="#eq:silly">$$
2 + 2 = 5
\label{eq:silly}
$$</span>

Unnumbered Section {#unnumbered-section .unnumbered}
------------------


<div id="fig:nonum" class="figure unnumbered">
![no numbering here (ˈjuːnɪˌkəʊd!)](image.png)

</div>

Multiple references {#multiple-references .unnumbered}
-------------------

We can refer to multiple things of the same type:
Figures [1](#fig:attr) and [2](#fig:attr2)

Or to multiple things of mixed type:
Section [0.1](#sec:expt), Equation [1](#eq:silly) and Figures [1](#fig:attr) and [2](#fig:attr2)
