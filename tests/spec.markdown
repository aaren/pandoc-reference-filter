0.1: Experiments with pandoc figures {#sec:expt .class1 .class2 key="value"}
------------------------------------


<div id="fig:attr" class="figure class1 class2" key=value>
![Figure 1: a figure that can be referred to](image.png)

</div>

Here is a reference to [Figure 1](#fig:attr) and here is one to
[Figure 2](#fig:attr2).

Here is reference to the section called [Section 0.1](#sec:expt).


<div id="fig:attr2" class="figure">
![Figure 2: another figure that can be referred to](image.png)

</div>

![figure with no attr](image.png)

Here is an equation:

$$
2 + 2 = 5
\label{eq:silly}
$$

Here is a reference to Equation $\eqref{eq:silly}$.

Unnumbered Section {#unnumbered-section .unnumbered}
------------------


<div id="fig:nonum" class="figure unnumbered">
![no numbering here](image.png)

</div>

