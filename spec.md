## Experiments with pandoc figures {#sec:expt .class1 .class2 key=value}

![a figure that can be referred to](image.png){#fig:attr .class1 .class2 key=value}

Here is a reference to #fig:attr and here is one to #fig:attr2.

Here is reference to the section called #sec:expt.

<div id="fig:attr2" class="figure">
![another figure that can be referred to](image.png)
</div>

![figure with no attr](image.png)


Here is an equation:

$$
2 + 2 = 5
\label{eq:silly}
$$

Here is a reference to #eq:silly.

## Unnumbered Section {-}

![no numbering here](image.png){#fig:nonum -}
