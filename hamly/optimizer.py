# -*- coding: utf-8 -*-

import ast
from .const import OPEN_TAG, WRITE, ESCAPE, TO_STRING, WRITE_MULTI, QUOTEATTR, WRITE_ATTRS
from .ast_utils import make_call, make_expr, make_tuple, ast_True, make_cond, copy_loc
from .escape import quoteattr
from .html import write_attrs, write_attrs_ast

class NameExtractorVisitor(ast.NodeVisitor):

    def __init__(self):
        self.names = []
        super(NameExtractorVisitor, self).__init__()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store) or isinstance(node.ctx, ast.Param):
            self.names.append(node.id)

    @classmethod
    def extract_names(cls, node):
        extractor = cls()
        extractor.visit(node)
        return extractor.names


class NameCollectorVisitor(ast.NodeVisitor):

    def __init__(self):
        self.names = []
        self.locals = [[]]
        super(NameCollectorVisitor, self).__init__()

    def visit_For(self, node):
        target_names = NameExtractorVisitor.extract_names(node.target)
        self.visit(node.iter)
        self.locals.append(target_names)
        self.locals.append([])
        for child in node.body:
            self.visit(child)
        self.locals.pop()
        self.locals.pop()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            name = node.id
            if name not in ("True", "False", "None",):
                for local in self.locals:
                    if name in local:
                        break
                else:
                    self.names.append(name)
        elif isinstance(node.ctx, ast.Store):
            self.locals[-1].append(node.id)

    def visit_FunctionDef(self, node):
        param_names = NameExtractorVisitor.extract_names(node.args)
        self.locals[-1].append(node.name)
        self.locals.append(param_names)
        self.locals.append([])
        for child in node.body:
            self.visit(child)
        self.locals.pop()
        self.locals.pop()


class StaticTreeVisitor(ast.NodeVisitor):

    def __init__(self):
        self.static = True
        super(StaticTreeVisitor, self).__init__()

    def visit_Name(self, node):
        self.static = False

    @classmethod
    def is_static(cls, node):
        visitor = cls()
        visitor.visit(node)
        return visitor.static


class OpenReplaceOptimizer(ast.NodeTransformer):

    def evaluate(self, node):
        return eval(compile(ast.fix_missing_locations(ast.Expression(node)), '', 'eval'))

    def _write(self, data):
        return make_expr(make_call(WRITE, data))

    def _to_string(self, data):
        return make_call(TO_STRING, data)

    def _escape(self, data):
        return make_call(ESCAPE, data)

    def _quoteattr(self, data):
        return make_call(QUOTEATTR, data)

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Call) and node.value.func.id == OPEN_TAG:
            static_args = []
            dynamic_args = []
            tagname = node.value.args[0].s
            for pair in node.value.args[1:]:
                if StaticTreeVisitor.is_static(pair):
                    static_args.append(pair)
                else:
                    dynamic_args.append(pair)

            block = [self._write("<%s" % tagname)]

            if not dynamic_args:
                static_attrs_data = []
                write_attrs(map(self.evaluate, static_args), static_attrs_data.append)
                block.append(self._write(''.join(static_attrs_data)))
            else:
                static_names = False
                all_args = static_args + dynamic_args
                for arg in all_args:
                    if not StaticTreeVisitor.is_static(arg.elts[0]):
                        break
                else:
                    static_names = True
                if static_names:
                    attrs_items = []
                    flatten_args = []
                    for arg in all_args:
                        value = arg.elts[1]
                        if StaticTreeVisitor.is_static(value):
                            value = ast.Str(str(self.evaluate(value)))
                        else:
                            value = self._quoteattr(value)
                        flatten_args.append((self.evaluate(arg.elts[0]), value))
                    write_attrs_ast(flatten_args, attrs_items.append)
                    for item in attrs_items:
                        block.append(self._write(item))
                else:
                    block.append(make_expr(make_call(WRITE_ATTRS, ast.Tuple(all_args, ast.Load()), ast.Name(WRITE, ast.Load()))))

            block.append(self._write(">\n"))
            return copy_loc(block, node)
        return node


class MultiWriteOptimizer(ast.NodeTransformer):

    def is_write(self, node):
        return isinstance(node, ast.Expr)\
            and isinstance(node.value, ast.Call)\
            and node.value.func.id == WRITE

    def join_strings(self, writes):
        result = []
        strings = []
        def _flush():
            if strings:
                result.append(ast.Str(''.join(strings)))
            strings[:] = []
        for item in writes:
            if isinstance(item, ast.Str):
                strings.append(item.s)
            else:
                _flush()
                result.append(item)
        _flush()
        return result

    def optimize_writes(self, body):
        result = []
        writes = []
        def _flush():
            if writes:
                joined = self.join_strings(writes)
                if len(joined) > 1:
                    result.append(make_expr(make_call(WRITE_MULTI, make_tuple(*joined))))
                else:
                    result.append(make_expr(make_call(WRITE, joined[0])))
                writes[:] = []

        for item in body:
            if self.is_write(item):
                writes.append(item.value.args[0])
            else:
                _flush()
                result.append(item)
        _flush()
        return map(self.visit, result)

    def visit_For(self, node):
        return copy_loc(ast.For(node.target, node.iter,
                                self.optimize_writes(node.body),
                                self.optimize_writes(node.orelse)),
                        node)

    def visit_If(self, node):
        return copy_loc(ast.If(node.test,
                               self.optimize_writes(node.body),
                               self.optimize_writes(node.orelse)),
                        node)

    def visit_FunctionDef(self, node):
        return copy_loc(ast.FunctionDef(node.name, node.args,
                                        self.optimize_writes(node.body),
                                        node.decorator_list),
                        node)

    def visit_Module(self, node):
        return copy_loc(ast.Module(self.optimize_writes(node.body)),
                        node)



OPTIMIZATION_PIPELINE = [OpenReplaceOptimizer, MultiWriteOptimizer]
# OPTIMIZATION_PIPELINE = []

def optimize(node):
    for optimizer_cls in OPTIMIZATION_PIPELINE:
        optimizer = optimizer_cls()
        node = optimizer.visit(node)
    
    names = NameCollectorVisitor()
    names.visit(node)
    names = list(set(names.names))
    for name in (ESCAPE, TO_STRING, QUOTEATTR, WRITE_ATTRS, "enumerate", "len"):
        if name in names:
            names.remove(name)
    arguments = ast.arguments(args=[ast.Name(name, ast.Param()) for name in names], vararg=None,
                              kwarg="__kw", defaults=[])# defaults=[ast.Name("None", ast.Load()) for name in names])
    return ast.Module([ast.FunctionDef(name="main", args=arguments, body=node.body, decorator_list=[])])
