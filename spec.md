## Experiments with pandoc figures {#sec:expt .class1 .class2 key=value}

![a figure that can be referred to](image.png){#fig:attr .class1 .class2 key=value}

Here is a reference to #fig:attr and here is one to #fig:attr2.

Here is reference to the section called #sec:expt.

<div id="fig:attr2" class="figure">
![another figure that can be referred to](image.png)
</div>

![figure with no attr](image.png)


Here is #eq:silly|:

$$
2 + 2 = 5
\label{eq:silly}
$$

## Unnumbered Section {-}

![no numbering here](image.png){#fig:nonum -}


## Multiple references {-}

We can refer to multiple things of the same type: #fig:attr#fig:attr2

Or to multiple things of mixed type: #fig:attr#fig:attr2#sec:expt#eq:silly
