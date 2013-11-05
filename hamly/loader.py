# -*- coding: utf-8 -*-

import ast
from .parser import parse
from .compiler import compile_tree
from .optimizer import optimize
from .const import WRITE, TO_STRING, ESCAPE, WRITE_MULTI, QUOTEATTR, WRITE_ATTRS

cache = {}

def get_template(filename):
    cached = cache.get(filename)

    if not cached:
        with open(filename) as fp:
            source = fp.read()

        tree = parse(source)
        compiled = compile_tree(tree)
        module = ast.Module(compiled)
        optimized = optimize(module)


        optimized.body.insert(0, ast.ImportFrom(module='hamly.escape',
                                                names=[ast.alias(name='escape', asname=ESCAPE),
                                                       ast.alias(name='quoteattr', asname=QUOTEATTR),
                                                       ast.alias(name='soft_unicode', asname=TO_STRING)], level=0))
        optimized.body.insert(0, ast.ImportFrom(module='hamly.html', names=[ast.alias(name='write_attrs', asname=WRITE_ATTRS)], level=0))

        template_source = ""
        try:
            from astmonkey import visitors
            template_source = visitors.to_source(optimized)
        except ImportError:
            pass

        code = compile(ast.fix_missing_locations(optimized), filename, 'exec')

        scope = {}
        exec code in scope
        main_fun = scope["main"]
        concat = ''.join

        def render(**kwargs):
            output = []
            context = {WRITE: output.append, WRITE_MULTI: output.extend}
            context.update(kwargs)
            main_fun(**context)
            return concat(output)

        setattr(render, "template_source", template_source)

        cached = render
        cache[filename] = cached

    return cached
