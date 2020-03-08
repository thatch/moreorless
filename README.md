# morelorless

This is a thin wrapper around `difflib.unified_diff` that Does The Right Thing
for "No newline at eof".  The args are also simplified compared to `difflib`:

```
moreorless.unified_diff(
    astr: str,
    bstr: str,
    filename: str,
    n: int = 3,
) -> str
```

# License

morelorless is copyright [Tim Hatch](http://timhatch.com/), and licensed under
the MIT license.  I am providing code in this repository to you under an open
source license.  This is my personal repository; the license you receive to
my code is from me and not from my employer. See the `LICENSE` file for details.
