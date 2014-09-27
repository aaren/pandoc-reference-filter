## Experiments with pandoc figures {#sec:expt}

![a figure that can be referred to](image.png){#fig:attr .class1 key=value}

Here is a reference to [this text is ignored](#fig:attr) and here is
one to [](#fig:attr2).

Here is reference to the section called [this text is also ignored](#sec:expt).

![another figure that can be referred to](image.png){#fig:attr2}

![figure with no attr](image.png)
