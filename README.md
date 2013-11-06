# haml for python
## faster than jinja2 and mako

### motivation

    $ python -m timeit -s 'from benchmark import j2_template, table' 'j2_template(table=table)'
    10 loops, best of 3: 31.9 msec per loop

    $ python -m timeit -s 'from benchmark import mako_template, table' 'mako_template(table=table)'
    10 loops, best of 3: 36.6 msec per loop

    $ python -m timeit -s 'from benchmark import hamly_template, table' 'hamly_template(table=table)'
    100 loops, best of 3: 6.54 msec per loop

even faster with python3

    $ python3.3 -m timeit -s 'from benchmark import hamly_template, table' 'hamly_template(table=table)'
    100 loops, best of 3: 3.83 msec per loop

###language

it's haml, but without (for now) some ruby-related features.
some examples:

```haml

%header

%nav.wide#main

.foo

.foo(bar='spam', some='eggs')

.foo(('bar', 'spam'), ('some', 'eggs'))

.foo(('bar', 'spam'), some='eggs', **{'class': 'more'}) / just like a python call

.foo{'class': 'spam'}

- def button(caption)
  .button= caption

+ button("look ma!")

- for index, value in enumerate(range(10))
  %div= index

plain text

```

### features

`hamly` converts template to `ast` like many others do.
the magic comes after transformation is done.
`hamly` optimizes resulting tree with several rules:

* do all tag attributes related stuff if possible (no dynamic names)
* unroll loops with literal iterator
* join strings in sequential writes
* combine sequential writes into one call
* inline functions with no starargs / kwargs
* escape literal values (strings and expressions)
* remove inlined function definitions

this template

```haml
- def foo(bar)
  %div.spam= bar
- for i in range(2)
  +foo(i)
```

will first compile to

```python
def main(_h_write, _h_write_multi, **__kw):

    def foo(bar):
        _h_open_tag('div', ('class', 'spam'))
        _h_write(_h_escape(bar))
        _h_write('\n')
        _h_write('</div>\n')
    for i in range(2):
        foo(i)
```

and then transformed to

```python
def main(_h_write, _h_write_multi, **__kw):
    _h_write(u"<div class='spam'>\n0\n</div>\n<div class='spam'>\n1\n</div>\n")
```

all writes are done with `append` and `extend` methods of `list`

