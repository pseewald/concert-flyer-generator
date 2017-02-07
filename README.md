# Concert Flyer Generator

This is a flyer generator intended to provide an automatic solution for print ready program flyers of recurring events. It is specifically targeting classical concerts and could be modified for other events. It uses a web form to collect data in json format and a python script to generate a pdf flyer from json using latex and tikz.

## Usage
1. go to the [web form](https://pseewald.github.io/concert-flyer-generator/) to specify the concert program.
2. download the json file.
3. Invoke the python script [generate_flyer.py](generate_flyer.py) as
```
./generate_flyer.py <json file>
```
to create the pdf.

## Options
A background can be specified by
```
./generate_flyer.py <json file> --background <background image>
```
Various formatting options (font, background color, spacings) can be specified by a `config` file in the same directory as `generate_flyer.py`. Example `config` files can be found in [examples](examples).

## Requirements

* XeLaTeX
* Python 2.7
* Latex packages: tikz, geometry, fontspec, background, setspace
* Python modules: [jsonschema](https://github.com/Julian/jsonschema), [jinja2](https://github.com/pallets/jinja), [latex](https://github.com/mbr/latex)
