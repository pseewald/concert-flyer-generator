#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *

import argparse, ConfigParser

import io
import os
import itertools

import json
import jsonschema

from jinja2.loaders import FileSystemLoader

import latex
from latex.jinja2 import make_env
from latex.build import LatexMkBuilder

# command line arguments
parser = argparse.ArgumentParser(description='Generate program flyer for concert.')
parser.add_argument("json", type=str, help="filename of program in json format (in).")
parser.add_argument("--pdf", type=str, help="filename of pdf (out). By default, use the base name of json input. Use '-' to suppress pdf output.")
parser.add_argument("--latex", type=str, help="filename of latex file (out). By default, no latex file is created.")
parser.add_argument("--background", type=str, help="filename of background (in). By default, a uniformly colored background is created")
parser.add_argument("--config", type=str, default='config', help="filename of config file (in) specifying formatting options. See file 'sample_config' for documentation")

if len(sys.argv)==1:
    parser.print_help()
    sys.exit(1)

args = parser.parse_args()
bgpic = args.background

build_latex = False
if args.latex:
    build_latex = True

if args.pdf is None:
    args.pdf = os.path.splitext(args.json)[0] + '.pdf'
    build_pdf = True
elif args.pdf == '-':
    build_pdf = False
else:
    build_pdf = True

# configuration file

config_defaults={'font': 'Helvetica',
                 'background color': 'blue!20',
                 'background opacity': '1',
                 'horizontal offset': '1',
                 'vertical offset': '1',
                 'node spacing': '0.5',
                 'column width': '[6.5, 11.4, 6.5]',
                 'column spacing':'0.3',
                 'row spacing': '0.05',
                 'line spacing': '0.4',
                 'program box margin': '0.3',
                 'time box margin': '0.3'}

config = ConfigParser.SafeConfigParser(config_defaults)

try:
    with io.open(args.config, 'r', encoding='utf-8') as configfile:
        config.readfp(io.StringIO("[_]\n" + configfile.read()))
except IOError:
    config.readfp(io.StringIO("[_]"))

font = config.get('_', 'font')
bgcol = config.get('_', 'background color')
hoff = config.getfloat('_', 'horizontal offset')
voff = config.getfloat('_', 'vertical offset')
nodesep = config.getfloat('_', 'node spacing')
colw = json.loads(config.get('_', 'column width'))
colsep = config.getfloat('_', 'column spacing')
rowsep = config.getfloat('_', 'row spacing')
linespacing = config.getfloat('_', 'line spacing')
pbox_margin = config.getfloat('_', 'program box margin')
tbox_margin = config.getfloat('_', 'time box margin')
bgopac = config.getfloat('_', 'background opacity')

mxsep = max(pbox_margin - colsep, 0.)  # separation for matrix border
mysep = max(pbox_margin - rowsep, 0.)

def key_in_dict(d, k):
    return k in d and d[k]

# what to build

with io.open("schema.json", 'r', encoding='utf-8') as infile:
    schema = json.loads(infile.read())

with io.open(args.json, 'r', encoding='utf-8') as infile:
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
        r"-{}cm".format(nodesep),
        r"-{}cm".format(nodesep)],
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
            if key_in_dict(piece, 'composer'):
                composer = piece['composer']

                tikzstr += r"{name} ".format(**composer)
                if key_in_dict(composer, 'yod') and key_in_dict(composer, 'yob'):
                    tikzstr += r"({yob}-{yod}) ".format(**composer)
                elif key_in_dict(composer, 'yob'):
                    tikzstr += r"(*{yob}) ".format(**composer)

                if key_in_dict(composer, 'arr'):
                    tikzstr += r"(arr. {arr}) ".format(**composer)

            tikzstr += r"&  {{{}\\".format(piece['title'][0].capitalize() + piece['title'][1:])
            nl += 1

            if key_in_dict(piece, 'movements'):
                for movement in piece['movements']:
                    nl += 1
                    tikzstr += r"\quad {}\\".format(movement[0].capitalize() + movement[1:])

            tikzstr += r"}&{"

            for performer in performance['ensemble'][np:nl]:
                tikzstr += r"{name} ({instrument})\\".format(**performer)

            tikzstr += r"}\\" + '\n'

            np = nl

        if np < len(performance['ensemble']):
            for performer in performance['ensemble'][np:]:
                tikzstr += r"&&{} ({})\\".format(performer['name'],performer['instrument'].lower())

    tikzstr += r'};' + '\n'

    tikzstr += (r'\draw[line width=1mm] (part {0}.north west) -- (part {0}.north east) -- '
                r'(part {0}.south east) -- (part {0}.south west) -- cycle;').format(ipart) + '\n'

    tikzstr += r'\node (time {3}) [time, {0}={4}cm of part {3}.{1}, anchor = {2}] {{\textbf{{{5}}}}};'.format(
        timeftd['pos'][ipart], timeftd['relpos'][ipart], timeftd['anchor'][ipart], ipart, nodesep, time) + '\n'

env = make_env(loader=FileSystemLoader('.'))

# builder to use xelatex instead of pdflatex
builder = LatexMkBuilder(pdflatex='xelatex')

# generate background
if not bgpic and build_pdf:
    tpl = env.get_template('background.tex')

    pdf = builder.build_pdf(tpl.render(color=bgcol))
    pdf.save_to("background.pdf")
    bgpic = 'background.pdf'
else:
    bgpic = 'background.pdf'

# generate flyer
tpl = env.get_template('flyer.tex')
inst_latex = tpl.render(font=font,
                        bgopac=bgopac,
                        bgpic=bgpic,
                        colw=colw,
                        colsep=colsep,
                        rowsep=rowsep,
                        mxsep=mxsep,
                        mysep=mysep,
                        tbox_margin=tbox_margin,
                        tikzstr=tikzstr,
                        linespacing=linespacing)

if build_latex:
    with io.open(args.latex, 'w', encoding='utf-8') as outfile:
        outfile.write(inst_latex)

if build_pdf:
    current_dir = os.path.abspath(os.path.dirname(__file__))
    pdf = builder.build_pdf(inst_latex, texinputs=[current_dir, ''])
    pdf.save_to(args.pdf)

