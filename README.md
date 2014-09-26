This pandoc filter implements an internal reference manager for
pandoc, making it possible to reference images, and sections that
have attribute tags.

For example, the markdown

```markdown
# The title {#ref:title}

![Some caption](filename.png){#ref:thefig}

As we can see in [](#ref:thefig).

As we can see in [](#ref:title).
```

Will be translated to the markdown

```markdown
![Figure 1: Some caption](filename.png)

As we can see in Figure 1.

As we can see in Section 1.
```

Usage:

```bash
pandoc spec.md --filter internal-references.py --to latex
```
