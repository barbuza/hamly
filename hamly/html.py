# -*- coding: utf-8 -*-

import ast

from .escape import quoteattr


def write_attrs_ast(attrs, _write):
    _atname = None
    for name, value in sorted(attrs):
        if name:
            if name != _atname:
                if _atname:
                    _write(ast.Str("'"))
                _write(ast.Str(" %s='" % name))
            else:
                _write(ast.Str(" "))
            _write(value)
            _atname = name
    if _atname:
        _write(ast.Str("'"))


def write_attrs(attrs, _write):
    _atname = None
    for name, value in sorted(attrs):
        if name:
            if name != _atname:
                if _atname:
                    _write("'")
                _write(" %s='" % name)
            else:
                _write(" ")
            _write(quoteattr(value))
            _atname = name
    if _atname:
        _write("'")
