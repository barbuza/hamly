# haml for python
## faster than jinja2 and mako

### benchmark

    $ python -m timeit -s 'from benchmark import j2_template, table' 'j2_template(table=table)'
    10 loops, best of 3: 31.9 msec per loop

    $ python -m timeit -s 'from benchmark import mako_template, table' 'mako_template(table=table)'
    10 loops, best of 3: 36.6 msec per loop

    $ python -m timeit -s 'from benchmark import hamly_template, table' 'hamly_template(table=table)'
    100 loops, best of 3: 6.54 msec per loop
