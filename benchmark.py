# -*- coding: utf-8 -*-

from jinja2 import Environment, FileSystemLoader
import hamly.loader

j2_env = Environment(loader=FileSystemLoader("./"))

j2_template = j2_env.get_template("bench.html").render
hamly_template = hamly.loader.get_template("bench.haml")

table = [range(10) for row in range(100)]
