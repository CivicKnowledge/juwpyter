import copy
import json
import logging
import re
import uuid
from datetime import datetime
from os.path import basename, dirname, exists, join
from pathlib import Path

import nbformat
from dateutil.parser import parse
from nbconvert.exporters.html import HTMLExporter
from nbconvert.filters.highlight import Highlight2HTML
from nbconvert.preprocessors import ExtractOutputPreprocessor, Preprocessor
from nbconvert.writers import FilesWriter
from nbformat.notebooknode import NotebookNode
from traitlets.config import Config, Unicode

import juwpyter.support.templates

from .util import slugify

logger = logging.getLogger(__name__)

class MetadataError(Exception):
    pass


class OrganizeMetadata(Preprocessor):
    """Move a lot of metadata around """

    package_url = Unicode(help='Metapack Package Url').tag(config=True)

    alt_title = None  # Title extracted from markdown, without a Title tag

    show_input = 'show'

    def __init__(self, **kw):
        self.front_matter = {'show_input': self.show_input}
        self.metadata = {}
        super().__init__(**kw)

    def preprocess(self, nb, resources):

        super().preprocess(nb, resources)

        nb.cells = [cell for cell in nb.cells if cell.source]

        self.front_matter['slug'] = slugify(self.front_matter.get('title', self.alt_title or str(uuid.uuid4())))

        # move the metadata we collected back into the notebook metadata.
        nb.metadata['frontmatter'] = self.front_matter
        nb.metadata['metapack'] = self.metadata

        return nb, resources

    def preprocess_cell(self, cell, resources, index):
        import yaml
        import re

        tags = [e.lower() for e in cell['metadata'].get('tags', [])]

        if 'frontmatter' in tags:
            d = yaml.safe_load(cell['source'])
            try:
                self.front_matter.update(d)
            except ValueError:
                raise

            cell.source = ''

        if 'metadata' in tags:
            d = yaml.load(cell['source'])
            self.metadata.update(d)
            cell.source = ''

        if 'title' in tags:
            self.front_matter['title'] = cell.source.strip().replace('#', '')
            m = resources.get('metadata', {})
            m['name'] = cell.source.strip().replace('#', '')
            resources['metadata'] = m
            cell.source = ''

        if 'show' in tags:
            cell['metadata']['show_input'] = 'show'

        if 'hide' in tags:
            cell['metadata']['show_input'] = 'hide'

        if cell.cell_type == 'markdown' and re.match(r'\#\s', cell.source.strip()):
            # Extract the first level 1 heading as the title, if a title isn't already defined
            m = re.match(r'\s*\#\s*(.*)$', cell.source.strip())
            if m and not self.alt_title:
                if 'title' not in self.front_matter:
                    self.front_matter['title'] = m.groups()[0]
                    cell.source = ''

                self.alt_title = m.groups()[0]

        if cell.cell_type == 'markdown' and 'description' in tags:
            self.front_matter['description'] = cell.source.strip().replace('#', '')
            cell.source = ''


        if 'show_input' not in cell['metadata']:
            cell['metadata']['show_input'] = self.front_matter['show_input']

        cell['metadata']['hide_input'] = (cell['metadata']['show_input'] == 'hide')

        return cell, resources

class SplitHeaders(Preprocessor):
    """ """

    def __init__(self, **kw):
        super().__init__(**kw)

    def preprocess(self, nb, resources):

        import re
        from copy import copy

        p = re.compile(r'^([#]+)\s+(.*)')

        new_cells = []

        for i, cell in enumerate(list(nb.cells)):

            if cell.get('cell_type') == 'markdown':
                proto_cell = copy(cell)
                proto_cell.source = ''

                next_cell = None

                # Breakout the heading lines into seperate cells.
                for l in cell.source.splitlines():
                    m = p.match(l)
                    if m:
                        # It was a heading line, so add it as a new cell

                        # Finish off the prior cell
                        if next_cell is not None:
                            new_cells.append(next_cell)

                        next_cell = copy(proto_cell)
                        next_cell.source += m.group(2).strip()
                        next_cell.heading_level = len(m.group(1))
                        new_cells.append(next_cell)

                        next_cell = None
                    elif len(l.strip()) == 0:
                        # a blank line, which means another paragraph
                        if next_cell is not None:
                            new_cells.append(next_cell)

                        next_cell = None
                    else:
                        if next_cell is None:
                            next_cell = copy(proto_cell)

                        next_cell.source += l.strip()+'\n'

                if next_cell is not None:
                    new_cells.append(next_cell)

            else:
                # Not a markwodn cell, so just move it over
                new_cells.append(cell)

        nb.cells = new_cells

        return nb, resources

class AttachementOutputExtractor(ExtractOutputPreprocessor):
    """Extract outputs from a notebook


    """

    #  def preprocess(self, nb, resources):
    #     return super().preprocess(nb, resources)

    def preprocess(self, nb, resources):

        for index, cell in enumerate(nb.cells):
            nb.cells[index], resources = self.preprocess_cell(cell, resources, index)

        return nb, resources  # return super().preprocess(nb, resources) ??

    def preprocess_cell(self, cell, resources, cell_index):
        """Also extracts attachments"""

        attach_names = []

        # Just move the attachment into an output

        for k, attach in cell.get('attachments', {}).items():
            for mime_type in self.extract_output_types:
                if mime_type in attach:

                    if 'outputs' not in cell:
                        cell['outputs'] = []

                    o = NotebookNode({
                        'data': NotebookNode({mime_type: attach[mime_type]}),
                        'metadata': NotebookNode({
                            'filenames': {mime_type: k}  # Will get re-written
                        }),
                        'output_type': 'display_data'
                    })

                    cell['outputs'].append(o)

                    attach_names.append((mime_type, k))

        nb, resources = super().preprocess_cell(cell, resources, cell_index)

        output_names = list(resources.get('outputs', {}).keys())

        if attach_names:
            # We're going to assume that attachments are only on Markdown cells, and Markdown cells
            # can't generate output, so all of the outputs were added.

            # reverse + zip matches the last len(attach_names) elements from output_names

            for output_name, (mimetype, an) in zip(reversed(output_names), reversed(attach_names)):
                # We'll post process to set the final output directory
                cell.source = re.sub(r'\(attachment:{}\)'.format(an),
                                     '(__IMGDIR__/{})'.format(output_name), cell.source)

        return nb, resources


class WordpressExporter(HTMLExporter):
    """ Export a python notebook to markdown, with frontmatter for Hugo.
    """

    staging_dir = Unicode(help="Root of the output directory").tag(config=True)

    @property
    def default_config(self):

        c = Config({})

        c.TemplateExporter.extra_template_paths = [dirname(juwpyter.support.templates.__file__)]
        c.TemplateExporter.template_file = 'html_wordpress.tpl'

        c.HTMLExporter.preprocessors = [
            'juwpyter.converter.SplitHeaders',
            'juwpyter.converter.OrganizeMetadata',
            AttachementOutputExtractor
        ]

        c.merge(super(WordpressExporter, self).default_config)

        c.ExtractOutputPreprocessor.enabled = False

        return c

    def get_creators(self, meta):

        for typ in ('wrangler', 'creator'):
            try:
                # Multiple authors
                for e in meta[typ]:
                    d = dict(e.items())
                    d['type'] = typ

                    yield d
            except AttributeError:
                # only one
                d = meta[typ]
                d['type'] = typ
                yield d
            except KeyError:
                pass

    def from_notebook_node(self, nb, resources=None, **kw):

        nb_copy = copy.deepcopy(nb)

        resources = self._init_resources(resources)

        if 'language' in nb['metadata']:
            resources['language'] = nb['metadata']['language'].lower()

        # Preprocess
        nb_copy, resources = self._preprocess(nb_copy, resources)

        # Other useful metadata
        if not 'date' in nb_copy.metadata.frontmatter:
            nb_copy.metadata.frontmatter['date'] = datetime.now().isoformat()

        resources.setdefault('raw_mimetypes', self.raw_mimetypes)

        resources['global_content_filter'] = {
            'include_code': not self.exclude_code_cell,
            'include_markdown': not self.exclude_markdown,
            'include_raw': not self.exclude_raw,
            'include_unknown': not self.exclude_unknown,
            'include_input': not self.exclude_input,
            'include_output': not self.exclude_output,
            'include_input_prompt': not self.exclude_input_prompt,
            'include_output_prompt': not self.exclude_output_prompt,
            'no_prompt': self.exclude_input_prompt and self.exclude_output_prompt,
        }

        langinfo = nb.metadata.get('language_info', {})
        lexer = langinfo.get('pygments_lexer', langinfo.get('name', None))
        self.register_filter('highlight_code',
                             Highlight2HTML(pygments_lexer=lexer, parent=self))

        def format_datetime(value, format='%a, %B %d'):

            return parse(value).strftime(format)

        self.register_filter('parsedatetime', format_datetime)

        slug = nb_copy.metadata.frontmatter.slug

        # Rebuild all of the image names
        for cell_index, cell in enumerate(nb_copy.cells):
            for output_index, out in enumerate(cell.get('outputs', [])):

                if 'metadata' in out:
                    for type_name, fn in list(out.metadata.get('filenames', {}).items()):
                        if fn in resources['outputs']:
                            html_path = join(slug, basename(fn))
                            file_path = join(self.staging_dir, html_path)

                            resources['outputs'][file_path] = resources['outputs'][fn]
                            del resources['outputs'][fn]

                            # Can't put the '/' in the join() or it will be absolute

                            out.metadata.filenames[type_name] = '/' + html_path

        output = self.template.render(nb=nb_copy, resources=resources)

        # Don't know why this isn't being set from the config
        # resources['output_file_dir'] = self.config.NbConvertApp.output_base

        # Setting full path to subvert the join() in the file writer. I can't
        # figure out how to set the output directories from this function
        resources['unique_key'] = join(self.staging_dir, slug)

        # Probably should be done with a postprocessor.
        output = re.sub(r'__IMGDIR__', '/' + slug, output)

        output = re.sub(r'<style scoped.*?>(.+?)</style>', '', output, flags=re.MULTILINE | re.DOTALL)

        resources['outputs'][join(self.staging_dir, slug + '.json')] = \
            json.dumps(nb_copy.metadata, indent=4).encode('utf-8')

        resources['outputs'][join(self.staging_dir, slug + '.ipynb')] = nbformat.writes(nb_copy).encode('utf-8')

        return output, resources


def convert_wordpress(nb_path, wp_path):
    if not exists(nb_path):
        logger.error("Notebook path does not exist: '{}' ".format(nb_path))

    c = Config()

    c.WordpressExporter.staging_dir = wp_path
    he = WordpressExporter(config=c, log=logger)

    output, resources = he.from_filename(nb_path)
    logger.info('Writing Notebook to Wordpress HTML')

    output_file = resources['unique_key'] + resources['output_extension']
    logger.info('    Writing '+ output_file)

    resource_outputs = []

    for k, v in resources['outputs'].items():
        logger.info('    Writing '+ k)
        resource_outputs.append(k)

    fw = FilesWriter()
    fw.build_directory = str(Path(wp_path).parent)
    fw.write(output, resources, notebook_name=resources['unique_key'])

    return output_file, resource_outputs
