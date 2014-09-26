## Experiments with pandoc figures {#sec:expt}

![
This is a multi-line 
caption
](image.png){#fig:attr}


![one line caption](image.png){#fig:attr2}

![figure with no attr](image.png)

Here is a reference to [this text is ignored](#fig:attr) and here is
one to [](#fig:attr2).

Here is reference to the section called [this text is not ignored](#sec:expt).
