#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *

import io
import os
import itertools

import json
import jsonschema

from jinja2.loaders import FileSystemLoader

import latex
from latex.jinja2 import make_env
from latex.build import LatexMkBuilder

##### May need configuration (everything in cm) #####
font = 'Montserrat'   # Font
hoff = 1.             # horizontal offset of tikzpicture
voff = hoff           # vertical offset of tikzpicture
vsep = 0.5            # separation between matrices and other nodes
colw = [6., 12.4, 6.] # length of the 3 columns
xsep = 0.3            # separation between nodes in x direction
ysep = 0.05           # separation between nodes in y direction
linespacing = 0.4     # line spacing (must be adapted to ysep)
mtsep = 0.3           # separation for time node
bgpic = r''           # background picture (filename)
bgcol = r'yellow!20'  # background color (if bgpic empty)
bgopac = 1.0          # background opacity
##### end configuration #####

mxsep = 0.3 - xsep  # separation for matrix border
mysep = 0.3 - ysep

# what to build
generate_latex = False
build_pdf = True

with io.open("program.schema.json", 'r', encoding='utf-8') as infile:
    schema = json.loads(infile.read())

with io.open("program.json", 'r', encoding='utf-8') as infile:
    program_full = json.loads(infile.read())

jsonschema.validate(program_full, schema)

# need to escape strings for latex:
def escape_dict(d):
    if isinstance(d, unicode):
        d = latex.escape(d)
    elif isinstance(d, list):
        d = [escape_dict(_) for _ in d]
    elif isinstance(d, dict):
        for k, v in d.iteritems():
            d[k] = escape_dict(d[k])
    return d

program_full = escape_dict(program_full)

# some formatting defaults:

partftd = {
    r"anchor": [
        r"north west",
        r"north east",
        r"north west"],
    r"xshift": [
        r"{}cm".format(hoff),
        r"0cm",
        r"0cm"],
    r"yshift": [
        r"-{}cm".format(voff),
        r"-{}cm".format(vsep),
        r"-{}cm".format(vsep)],
    r"pos": [
        r"current page.north west",
        r"time 0.north |- part 0.south",
        r"time 1.south |- part 1.south"]}

timeftd = {r"pos": [r"right", r"left", r"right"],
           r"relpos": [r"north east", r"north west", r"north east"],
           r"anchor": [r"south west", r"north west", r"south west"]}

# build tikz string
tikzstr = r''
for ipart, part in enumerate(program_full):
    time = part['time']
    performances = part['performances']

    tikzstr += r'\matrix (part {}) [program, anchor = {}, xshift = {}, yshift = {}] at ({})'.format(
               ipart,
               partftd['anchor'][ipart],
               partftd['xshift'][ipart],
               partftd['yshift'][ipart],
               partftd['pos'][ipart])

    tikzstr += r'{' + '\n'

    draw_line = False
    for performance in performances:
        if draw_line:
            tikzstr += r"&&\\" + '\n'
            tikzstr += (r"\draw (-{0}cm,0) -- ({0}cm,0); & \draw (-{1}cm,0) -- ({1}cm,0); "
                        r"& \draw (-{2}cm,0) -- ({2}cm,0); \\").format(*[_ * 0.5 for _ in colw]) + '\n'
            tikzstr += r"&&\\" + '\n'
        draw_line = True
        [np, nl] = [0, 0]  # number of performers, line count
        for piece in performance['pieces']:
            if 'composer' in piece:
                composer = piece['composer']

                tikzstr += r"{name} ".format(**composer)
                if 'yod' in composer and 'yob' in composer:
                    tikzstr += r"({yob}-{yod}) ".format(**composer)
                elif 'yob' in composer:
                    tikzstr += r"(*{yob}) ".format(**composer)

                if 'arr' in composer:
                    tikzstr += r"(arr. {arr}) ".format(**composer)

            tikzstr += r"&  {{{name}\\".format(**piece)
            nl += 1

            if 'movements' in piece:
                for movement in piece['movements']:
                    nl += 1
                    tikzstr += r"\quad {}\\".format(movement)

            tikzstr += r"}&{"

            for performer in performance['ensemble'][np:nl]:
                tikzstr += r"{name} ({instrument})\\".format(**performer)

            tikzstr += r"}\\" + '\n'

            np = nl

        if np < len(performance['ensemble']):
            for performer in performance['ensemble'][np:]:
                tikzstr += r"&&{name} ({instrument})\\".format(**performer)

    tikzstr += r'};' + '\n'

    tikzstr += (r'\draw[line width=1mm] (part {0}.north west) -- (part {0}.north east) -- '
                r'(part {0}.south east) -- (part {0}.south west) -- cycle;').format(ipart) + '\n'

    tikzstr += r'\node (time {3}) [time, {0}={4}cm of part {3}.{1}, anchor = {2}] {{\textbf{{{5}}}}};'.format(
        timeftd['pos'][ipart], timeftd['relpos'][ipart], timeftd['anchor'][ipart], ipart, vsep, time) + '\n'

env = make_env(loader=FileSystemLoader('.'))

# builder to use xelatex instead of pdflatex
builder = LatexMkBuilder(pdflatex='xelatex')

# generate background
if not bgpic:
    tpl = env.get_template('background.tex')

    pdf = builder.build_pdf(tpl.render(color=bgcol))
    pdf.save_to("background.pdf")
    bgpic = "background.pdf"

# generate flyer
tpl = env.get_template('flyer.tex')
inst_latex = tpl.render(font=font,
                        bgopac=bgopac,
                        bgpic=bgpic,
                        colw=colw,
                        xsep=xsep,
                        ysep=ysep,
                        mxsep=mxsep,
                        mysep=mysep,
                        mtsep=mtsep,
                        tikzstr=tikzstr,
                        linespacing=linespacing)

if generate_latex:
    with io.open("flyer_inst.tex", 'w', encoding='utf-8') as outfile:
        outfile.write(inst_latex)

if build_pdf:
    current_dir = os.path.abspath(os.path.dirname(__file__))
    pdf = builder.build_pdf(inst_latex, texinputs=[current_dir, ''])
    pdf.save_to("flyer.pdf")
