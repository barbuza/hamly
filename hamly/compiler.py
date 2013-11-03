# -*- coding: utf-8 -*-

import ast

from .parser import TagNode, ControlNode, TextNode, OutputNode, StatementNode
from .const import OPEN_TAG, WRITE, ESCAPE, TO_STRING
from .ast_utils import make_call, make_expr, make_tuple, ast_True, copy_loc


def dynamic_attrs_to_args(dynamic_attrs):
    call = ast.parse("_(%s)" % dynamic_attrs).body[0].value
    args = call.args
    for kw in call.keywords:
        args.append(make_tuple(kw.arg, kw.value))
    if call.kwargs:
        for key, value in zip(call.kwargs.keys, call.kwargs.values):
            args.append(make_tuple(key, value))
    return args


def tagnode_to_ast(node):
    callargs = [ast.Str(node.tagname)]
    if node.dynamic_attrs:
        callargs.extend(dynamic_attrs_to_args(node.dynamic_attrs))
    if node.attrs:
        for key, value in node.attrs.items():
            callargs.append(make_tuple(key, value))
    block = sum(map(node_to_ast, node.children), [make_expr(make_call(OPEN_TAG, *callargs))])
    block.append(make_expr(make_call(WRITE, "</%s>\n" % node.tagname)))
    return block


def controlnode_to_ast(node):
    mod = ast.parse("%s\n  pass" % node.code)
    ctrl = mod.body[0]
    ctrl.body = sum(map(node_to_ast, node.children), [])
    return [ctrl]


def textnode_to_ast(node):
    return [make_expr(make_call(WRITE, node.text + "\n"))]


def outputnode_to_ast(node):
    value = ast.parse(node.expr).body[0].value
    return [make_expr(make_call(WRITE, make_call(ESCAPE, value))),
            make_expr(make_call(WRITE, "\n"))]


def statementnode_to_ast(node):
    mod = ast.parse(node.st)
    if isinstance(mod.body[0], ast.Expr) or isinstance(mod.body[0], ast.Assign):
        return [mod.body[0]]
    else:
        RuntimeError("can't conver %r to ast" % node)


def node_to_ast(node):
    def _block():
        if isinstance(node, TagNode):
            return tagnode_to_ast(node)
        elif isinstance(node, ControlNode):
            return controlnode_to_ast(node)
        elif isinstance(node, TextNode):
            return textnode_to_ast(node)
        elif isinstance(node, OutputNode):
            return outputnode_to_ast(node)
        elif isinstance(node, StatementNode):
            return statementnode_to_ast(node)
        else:
            raise RuntimeError("can't convert %r to ast" % node)
    try:
        return [copy_loc(item, node.line.num + 1) for item in _block()]
    except SyntaxError:
        raise RuntimeError("compiler failed near '%s' at line %i" % (node.line.content, node.line.num))


def compile_tree(nodes):
    block = []
    for node in nodes:
        block.extend(node_to_ast(node))
    return block
