# -*- coding: utf-8 -*-

import re
from collections import namedtuple


Line = namedtuple("Line", ("num", "indent", "content", "children"))


class Node(object):

    pass


class TagNode(Node):

    def __init__(self, tagname, attrs, dynamic_attrs=None):
        self.tagname = tagname
        self.attrs = attrs
        self.dynamic_attrs = dynamic_attrs
        self.children = []


class ControlNode(Node):

    def __init__(self, code):
        self.code = code
        self.children = []


class TextNode(Node):

    def __init__(self, text):
        self.text = text


class OutputNode(Node):

    def __init__(self, expr):
        self.expr = expr


class StatementNode(Node):

    def __init__(self, st):
        self.st = st


def parse_lines(source):
    lines = []
    for index, data in enumerate(source.split("\n")):
        if not data.strip() or data.strip().startswith("/"):
            continue
        indent = len(data) - len(data.lstrip())
        if indent % 2:
            raise IndentationError("bad indent on line %s" % (index + 1))
        indent = indent / 2
        line = Line(index + 1, indent, data.strip(), [])
        lines.append(line)
    return lines


def make_tree(lines):
    levels = {}
    roots = []
    for line in lines:
        if line.indent:
            levels[line.indent - 1].children.append(line)
        else:
            roots.append(line)
        levels[line.indent] = line
    return roots


def linetree_to_nodetree(lines):
    nodes = []
    for line in lines:
        node = line_to_node(line)
        if line.children:
            if not hasattr(node, "children"):
                raise RuntimeError("bad nesting near line %s" % line.num)
            node.children.extend(linetree_to_nodetree(line.children))
        nodes.append(node)
    return nodes


def line_to_node(line):
    def _node():
        if line.content[0] in ".%#":
            return line_to_tag(line)
        elif line.content[0] == "-":
            return line_to_control(line)
        elif line.content[0] == "=":
            return line_to_output(line)
        elif line.content[0] == "+":
            return line_to_statement(line)
        else:
            return line_to_text(line)
    node = _node()
    node.line = line
    return node


def line_to_tag(line):
    data = line.content
    attrs = {}
    tagname = "div"
    while data and data[0] in "%.#":
        word = re.match(r'^\w+', data[1:]).group()
        if data[0] == "%":
            tagname = word
        elif data[0] == ".":
            classname = attrs.get("class", None)
            if classname:
                classname += " " + word
            else:
                classname = word
            attrs["class"] = classname
        elif data[0] == "#":
            attrs["id"] = word
        data = data[len(word) + 1:]
    dynamic_attrs = None
    if data and data[0] == "(":
        open_braces = 0
        for idx in range(len(data)):
            if data[idx] == "(":
                open_braces += 1
            elif data[idx] == ")":
                open_braces -= 1
            if open_braces is 0:
                break
        assert open_braces is 0
        dynamic_attrs = data[1:idx]
        data = data[idx + 1:]
    if data and data[0] == "{":
        open_braces = 0
        for idx in range(len(data)):
            if data[idx] == "{":
                open_braces += 1
            elif data[idx] == "}":
                open_braces -= 1
            if open_braces is 0:
                break
        assert open_braces is 0
        dynamic_attrs = "**{%s}" % data[1:idx]    
        data = data[idx + 1:]
    data = data.strip()
    node = TagNode(tagname, attrs, dynamic_attrs)
    if data:
        node.children.append(line_to_node(Line(0, 0, data, None)))
    return node


def line_to_control(line):
    code = line.content[1:].strip()
    if not code.endswith(":"):
        code = code + ":"
    return ControlNode(code)


def line_to_output(line):
    return OutputNode(line.content[1:].strip())


def line_to_statement(line):
    return StatementNode(line.content[1:].strip())


def line_to_text(line):
    return TextNode(line.content)


def parse(source):
    lines = parse_lines(source)
    tree = make_tree(lines)
    return linetree_to_nodetree(tree)
