# -*- coding: utf-8 -*-

import ast


def scalar_to_ast(value):
    if isinstance(value, basestring):
        return ast.Str(value)
    elif isinstance(value, int) or isinstance(value, float):
        return ast.Num(value)
    else:
        return value


def make_call(name, *args):
    ast_args = map(scalar_to_ast, args)
    return ast.Call(ast.Name(name, ast.Load()), ast_args, [], None, None)


def make_expr(node):
    return ast.Expr(node)


def make_tuple(*elts):
    ast_elts = map(scalar_to_ast, elts)
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
