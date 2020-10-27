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

from juwpyter import __version__

from .converter import convert_wordpress
from .util import ensure_dir
from .wp import publish_wp

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

    parser.add_argument('-n', '--no-op', help='Do everything but submit the post', action='store_true')

    parser.add_argument('-s', '--site_name', help="Site name, in the .metapack.yaml configuration file")

    parser.add_argument('-p', '--publish', help='Set the post state to published, rather than draft',
                        action='store_true')

    parser.add_argument('source', help="Path to the notebook")



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

    output_file, resources = convert_wordpress(args.source, p)

    r, post = publish_wp(args.site_name, output_file, resources, args)
    print("Post url: ", post.link)



def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
