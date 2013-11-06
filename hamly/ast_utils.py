# -*- coding: utf-8 -*-

import sys
import ast

if sys.version_info[0] < 3:
    def is_string(value):
        return isinstance(value, basestring)
else:
    def is_string(value):
        return isinstance(value, str)

def scalar_to_ast(value):
    if value is True:
        return ast.Name("True", ast.Load())
    elif value is False:
        return ast.Name("False", ast.Load())
    elif value is None:
        return ast.Name("None", ast.Load())
    elif is_string(value):
        return ast.Str(value)
    elif isinstance(value, int) or isinstance(value, float):
        return ast.Num(value)
    elif isinstance(value, list):
        return ast.List([scalar_to_ast(x) for x in value], ast.Load())
    elif isinstance(value, tuple):
        return ast.Tuple([scalar_to_ast(x) for x in value], ast.Load())
    elif isinstance(value, dict):
        return ast.Dict([scalar_to_ast(x) for x in value.keys()],
                        [scalar_to_ast(x) for x in value.values()])
    else:
        return value


def make_call(name, *args):
    ast_args = [scalar_to_ast(x) for x in args]
    return ast.Call(ast.Name(name, ast.Load()), ast_args, [], None, None)


def make_expr(node):
    return ast.Expr(node)


def make_tuple(*elts):
    ast_elts = [scalar_to_ast(x) for x in elts]
    return ast.Tuple(ast_elts, ast.Load())


def make_test(test, body, orelse):
    return ast.IfExp(test, body, orelse)


def make_cond(test, body):
    if not isinstance(body, list):
        body = [body]
    return ast.If(test, body, [])


def ast_True():
    return ast.Name("True", ast.Load())


def copy_loc(target, source):
    if isinstance(source, int):
        source = ast.Str("", lineno=source, col_offset=0)
    if isinstance(target, list):
        return [copy_loc(item, source) for item in target]
    return ast.copy_location(target, source)


class DefinesVisitor(ast.NodeVisitor):

    def __init__(self):
        self.defines = False
        super(DefinesVisitor, self).__init__()

    def visit_FunctionDef(self, node):
        self.defines = True


def defines_functions(tree):
    if isinstance(tree, list):
        defines = False
        for item in tree:
            if defines_functions(item):
                defines = True
                break
        return defines
    visitor = DefinesVisitor()
    visitor.visit(tree)
    return visitor.defines
