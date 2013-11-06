# -*- coding: utf-8 -*-

from jinja2 import Environment, FileSystemLoader
from mako.template import Template as MakoTemplate
import hamly.loader

j2_env = Environment(loader=FileSystemLoader("./"))

j2_template = j2_env.get_template("bench.html").render
hamly_template = hamly.loader.get_template("bench.haml")

with open("bench.mako") as m_tmpl:
    mako_template = MakoTemplate(m_tmpl.read()).render


table = [dict(a=1,b=2,c=3,d=4,e=5,f=6,g=7,h=8,i=9,j=10)
          for x in range(1000)]

# print "-" * 80
# print(hamly_template.template_source)

# print(hamly_template(table=[dict(a=1,b=2) for x in range(2)]))
