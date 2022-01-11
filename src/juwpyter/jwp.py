# -*- coding: utf-8 -*-
"""
This is a skeleton file that can serve as a starting point for a Python
console script. To run this script uncomment the following lines in the
[options.entry_points] section in setup.cfg:

    console_scripts =
         fibonacci = juwpyter.skeleton:run

Then run `python setup.py install` which will install the command `fibonacci`
inside your current environment.
Besides console scripts, the header (i.e. until _logger...) of this file can
also be used as template for Python modules.

Note: This skeleton file can be safely removed if not needed!
"""

import argparse
import logging
import sys

import yaml

from juwpyter import __version__

from .converter import convert_wordpress
from .util import ensure_dir
from .wp import PublishException, get_site_names, get_wp, publish_wp

__author__ = "Eric Busboom"
__copyright__ = "Eric Busboom"
__license__ = "mit"

_logger = logging.getLogger(__name__)


def parse_args(args):
    """Publish a Jupyter notebook to Wordpress
    """
    parser = argparse.ArgumentParser(
        'jwp',
        description=parse_args.__doc__
    )

    parser.add_argument(
        "--version",
        action="version",
        version="juwpyter {ver}".format(ver=__version__))

    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO)
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG)

    parser.add_argument('-H', '--header', help='Dump YAML of notebook header', action='store_true')



    parser.add_argument('-s', '--site_name', help="Site name, in the .metapack.yaml configuration file")


    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-p', '--publish', help='Set the post state to published, rather than draft',
                        action='store_true')

    group.add_argument('-g', '--get', help='Get and display the post data and exit. ',
                        action='store_true')

    group.add_argument('-S', '--show', help="Show the HTML of the article, and don't publish ",
                        action='store_true')

    group.add_argument('-n', '--new', help='Create a new notebook',
                        action='store_true')

    group.add_argument('-f', '--frontmatter', help='Add frontmatter to notebook',
                        action='store_true')

    group.add_argument('-N', '--no-op', help='Do everything but submit the post', action='store_true')

    parser.add_argument('source', help="Path to the notebook", nargs='?')

    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stdout,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    _logger.debug("")

    p = '/tmp/metapack-wp-notebook/'
    ensure_dir(p)

    def check_site_name():
        if not args.site_name:
            print("ERROR: Must specify a publication site name")
            sep = '\n    '
            print("Configured site names are:\n")
            print(sep + sep.join(get_site_names()))
            sys.exit(1)

    def check_source():
        if not args.source:
            print("ERROR: Must specify a source")
            sys.exit(1)

    def make_output():
        check_site_name()
        check_source()
        output_file, resources = convert_wordpress(args.source, p)
        return output_file, resources

    if args.new:
        new_notebook(args)

    elif args.frontmatter:
        check_source()
        update_frontmatter(args.source)

    elif args.show:
        check_source()
        output_file, resources = make_output()

        print(f"=== Displaying {output_file} " )
        with open(output_file) as f:
            for l in f.readlines():
                print(l)

    elif args.get:

        output_file, resources = make_output()

        post = get_wp(args.site_name, output_file, resources, args)
        if post:
            from pprint import pprint
            post.content = "<content elided>"
            print(pprint(post.struct))

        else:
            print('Did not find a post for this notebook')
    elif args.publish:
        output_file, resources = make_output()
        r, post = publish_wp(args.site_name, output_file, resources, args)
        if post:
            print("Post url: ", post.link)
    elif args.no_op:
        check_source()
        output_file, resources = make_output()
    else:
        assert False, 'Should not get here'

def run():
    """Entry point for console_scripts
    """
    try:
        main(sys.argv[1:])
    except PublishException as e:
        _logger.error(e)

def update_frontmatter(path):
    import nbformat
    from uuid import uuid4

    nb = nbformat.read(path, as_version=4)

    def get_tagged(t):
        for c in nb.cells:
            try:
                if t in c.metadata.tags:
                    return c
            except AttributeError:
                pass

        return False

    def has_tag(t):
        if get_tagged(t) is not False:
            return True
        else:
            return False

    fm_cells = []
    adds = []

    if not has_tag('frontmatter'):
        adds.append("frontmatter")
        fm_cells.append(nbformat.v4.new_raw_cell(f"""
show_input: hide
github:
identifier: {uuid4()}
authors:
- email: bob@example.com
  name: Bob Bobson
  organization: Bobcom
  type: Analyst
tags:
- tag
categories:
- group
        """, metadata={'tags': ['frontmatter']}))
    else:
        c = get_tagged('frontmatter')
        d = yaml.safe_load(c['source'])
        if not 'identifier' in d:
            d['identifier'] = str(uuid4())
            c['source'] = yaml.dump(d)

            adds.append("identity")

    if not has_tag('Title'):
        adds.append("title")
        fm_cells.append(nbformat.v4.new_markdown_cell('# Title', metadata={'tags': ['Title']}))

    if not has_tag('Description'):
        adds.append("description")
        fm_cells.append(nbformat.v4.new_markdown_cell('Description',
                                                      metadata={'tags': ['Description']}))

    nb.cells = fm_cells + nb.cells

    if adds:
        print(f"Added to {path}: {','.join(adds)}")
        nbformat.write(nb, path)
    else:
        print(f"Added nothing: {path} is already complete")


def new_notebook(args):
    import requests
    from pathlib import Path

    url = 'https://raw.githubusercontent.com/CivicKnowledge/juwpyter/main/support/Template.ipynb'

    r = requests.get(url, allow_redirects=True)
    r.raise_for_status()

    p = Path(args.source)

    nb_path = Path(f'{p.stem}.ipynb')

    ensure_dir(nb_path.parent)

    if nb_path.exists():
        print(f'Notebook already exists: {nb_path}')
    else:
        with  nb_path.open('wb') as f:
            f.write(r.content)

        # To update the identifier
        update_frontmatter(nb_path)

        print(f'Created {nb_path}')


if __name__ == "__main__":
    run()
