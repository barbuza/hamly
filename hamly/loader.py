# -*- coding: utf-8 -*-

import sys
import ast

from six import exec_

from .escape import escape, quoteattr, soft_unicode
from .html import write_attrs
from .parser import parse
from .compiler import compile_tree
from .optimizer import optimize
from .const import (WRITE, TO_STRING, ESCAPE, WRITE_MULTI,
                    QUOTEATTR, WRITE_ATTRS, MAIN)

cache = {}

def get_template(filename):
    cached = cache.get(filename)

    if not cached:
        with open(filename) as fp:
            source = fp.read()#.decode("utf-8")

        tree = parse(source)
        compiled = compile_tree(tree)
        module = ast.Module(compiled)
        optimized = optimize(module)

        template_source = ""
        try:
            from astmonkey import visitors
            template_source = visitors.to_source(optimized)
        except ImportError:
            try:
                import codegen
                template_source = codegen.to_source(optimized)
            except ImportError:
                template_source = ""

        # if sys.version_info[0] < 3:
        #     optimized.body.insert(0, ast.ImportFrom("hamly.escape",
        #                                             [ast.alias("escape", ESCAPE),
        #                                              ast.alias("quoteattr", QUOTEATTR),
        #                                              ast.alias("soft_unicode", TO_STRING)],
        #                                             0))
        #     optimized.body.insert(0, ast.ImportFrom("hamly.html", [ast.alias("write_attrs", WRITE_ATTRS)], 0))

        code = compile(ast.fix_missing_locations(optimized), filename, "exec")

        globs = {
            ESCAPE: escape,
            QUOTEATTR: quoteattr,
            TO_STRING: soft_unicode,
            WRITE_ATTRS: write_attrs
        }        

        scope = {}
        exec_(code, globs, scope)
        main_fun = scope[MAIN]
        concat = "".join

        def render(**kwargs):
            output = []
            context = {WRITE: output.append, WRITE_MULTI: output.extend}
            context.update(kwargs)
            main_fun(**context)
            return concat(output)

        setattr(render, "template_source", template_source)

        cached = render
        # cache[filename] = cached

    return cached
