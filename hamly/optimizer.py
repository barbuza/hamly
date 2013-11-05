# -*- coding: utf-8 -*-

import ast
import copy

from .const import OPEN_TAG, WRITE, ESCAPE, TO_STRING, WRITE_MULTI, QUOTEATTR, WRITE_ATTRS
from .ast_utils import (make_call, make_expr, make_tuple, ast_True,
                        make_cond, copy_loc, scalar_to_ast, defines_functions, )
from .escape import quoteattr, escape
from .html import write_attrs, write_attrs_ast


INTERNALS = [WRITE, OPEN_TAG, WRITE_MULTI, QUOTEATTR, WRITE_ATTRS, ESCAPE,
             "True", "False", "None", "range", "xrange", "enumerate", "len", "dict"]


class NameExtractorVisitor(ast.NodeVisitor):

    def __init__(self):
        self.names = []
        super(NameExtractorVisitor, self).__init__()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store) or isinstance(node.ctx, ast.Param):
            if node.id not in self.names:
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
            if name not in INTERNALS:
                for local in self.locals:
                    if name in local:
                        break
                else:
                    self.names.append(name)
        elif isinstance(node.ctx, ast.Store):
            self.locals[-1].append(node.id)

    def visit_ListComp(self, node):
        for gen in node.generators:
            self.visit(gen)
        gen_names_extractor = NameExtractorVisitor()
        for gen in node.generators:
            gen_names_extractor.visit(gen)
        self.locals.append(gen_names_extractor.names)
        self.locals.append([])
        self.visit(node.elt)
        self.locals.pop()
        self.locals.pop()

    def visit_FunctionDef(self, node):
        param_names = NameExtractorVisitor.extract_names(node.args)
        self.locals[-1].append(node.name)
        self.locals.append(param_names)
        self.locals.append([])
        for child in node.body:
            self.visit(child)
        self.locals.pop()
        self.locals.pop()


class StaticTreeVisitor(object):

    @classmethod
    def is_static(cls, node):
        collector = NameCollectorVisitor()
        collector.visit(node)
        return not collector.names


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
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == OPEN_TAG:
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
            and isinstance(node.value.func, ast.Name)\
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


class SubstituteVisitor(ast.NodeTransformer):

    def __init__(self, name, replacement):
        self.name = name
        self.replacement = replacement

    def visit_Name(self, node):
        if node.id == self.name and isinstance(node.ctx, ast.Load):
            return self.replacement
        return node


class UnloopOptimizer(ast.NodeTransformer):

    def __init__(self):
        self._unloop = False
        super(UnloopOptimizer, self).__init__()

    def evaluate(self, node):
        return eval(compile(ast.fix_missing_locations(ast.Expression(node)), '', 'eval'))

    def visit_For(self, node):
        if StaticTreeVisitor.is_static(node.iter):
            names = NameExtractorVisitor.extract_names(node.target)
            iterable = self.evaluate(node.iter)
            block = []
            for value in self.evaluate(node.iter):
                iter_assign = ast.Assign([node.target], scalar_to_ast(value))
                code = compile(ast.fix_missing_locations(ast.Module([iter_assign])), '', 'exec')
                scope = {}
                body = map(copy.deepcopy, node.body)
                exec code in scope
                for st in body:
                    for name in names:
                        st = SubstituteVisitor(name, scalar_to_ast(scope[name])).visit(st)
                    block.append(st)
            self._unloop = True
            return block
        return node

    def perform(self, node):
        result = self.visit(node)
        if self._unloop:
            return UnloopOptimizer().perform(result)
        return result



class StaticEscapeOptimizer(ast.NodeTransformer):

    def evaluate(self, node):
        return eval(compile(ast.fix_missing_locations(ast.Expression(node)), '', 'eval'))

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == WRITE:
            call = node.args[0]
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id in (ESCAPE, QUOTEATTR):
                if StaticTreeVisitor.is_static(call.args[0]):
                    if call.func.id == ESCAPE:
                        node = make_call(WRITE, ast.Str(escape(self.evaluate(call.args[0]))))
                    elif call.func.id == QUOTEATTR:
                        node = make_call(WRITE, ast.Str(quoteattr(self.evaluate(call.args[0]))))
        return node



class InlineOptimizer(ast.NodeTransformer):

    def __init__(self):
        self.functions = [[]]
        self._inline = False
        super(InlineOptimizer, self).__init__()

    def visit_Expr(self, node):
        if not isinstance(node.value, ast.Call):
            return node
        if isinstance(node.value.func, ast.Name)\
                    and node.value.func.id not in (WRITE, WRITE_MULTI, ESCAPE, QUOTEATTR)\
                    and not node.value.keywords\
                    and not node.value.starargs\
                    and not node.value.kwargs:
            impl = None
            for name, impl in sum(reversed(self.functions), []):
                if name == node.value.func.id:
                    break
            else:
                return node
            if not impl or impl.args.vararg or impl.args.kwarg:
                return node
            undefined = object()
            min_args = len(impl.args.args) - len(impl.args.defaults)
            max_args = len(impl.args.args)
            if len(node.value.args) < min_args or len(node.value.args) > max_args:
                return node
            body = copy.deepcopy(impl.body)
            values = node.value.args[:]
            values += impl.args.defaults[len(values) - max_args:]
            for arg, value in zip(impl.args.args, values):
                body = map(SubstituteVisitor(arg.id, value).visit, body)
            self._inline = True
            return body
        return node

    def visit_FunctionDef(self, node):
        if not defines_functions(node.body):
            self.functions[-1].append((node.name, node))
        self.functions.append([])
        new_body = []
        for child in node.body:
            result = self.visit(child)
            if isinstance(result, list):
                new_body.extend(result)
            else:
                new_body.append(result)
        node.body = new_body
        self.functions.pop()
        return node

    def perform(self, node):
        result = self.visit(node)
        if self._inline:
            return InlineOptimizer().perform(result)
        return result


OPTIMIZATION_PIPELINE = [OpenReplaceOptimizer, UnloopOptimizer, InlineOptimizer,
                         StaticEscapeOptimizer, MultiWriteOptimizer]


def optimize(node):
    for optimizer_cls in OPTIMIZATION_PIPELINE:
        optimizer = optimizer_cls()
        if hasattr(optimizer, "perform"):
            node = optimizer.perform(node)
        else:
            node = optimizer.visit(node)
    
    names = NameCollectorVisitor()
    names.visit(node)
    names = list(set(names.names))
    names.extend((WRITE, WRITE_MULTI))
    arguments = ast.arguments(args=[ast.Name(name, ast.Param()) for name in names], vararg=None,
                              kwarg="__kw", defaults=[])
    return ast.Module([ast.FunctionDef(name="main", args=arguments, body=node.body, decorator_list=[])])
