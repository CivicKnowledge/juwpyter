import json
import logging
from functools import lru_cache
from os.path import basename
from textwrap import dedent
from uuid import uuid4
from xmlrpc import client as xmlrpc_client
from xmlrpc.client import Fault

import yaml
from metapack.cli.core import get_config
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.media import GetMediaLibrary, UploadFile
from wordpress_xmlrpc.methods.posts import EditPost, GetPost, NewPost

logger = logging.getLogger(__name__)

class PublishException(Exception):
    pass

def cust_field_dict(post):
    try:
        return dict((e['key'], e['value']) for e in post.custom_fields)
    except (KeyError, AttributeError):
        return {}


def set_custom_field(post, key, value):
    if not hasattr(post, 'custom_fields') or not key in [e['key'] for e in post.custom_fields]:

        if not hasattr(post, 'custom_fields'):
            post.custom_fields = []

        post.custom_fields.append({'key': key, 'value': value})


@lru_cache()
def get_posts(wp):
    """Get and memoize all posts"""
    from wordpress_xmlrpc.methods.posts import GetPosts

    all_posts = []

    offset = 0
    increment = 20
    while True:
        posts = wp.call(GetPosts({'number': increment, 'offset': offset}))
        if len(posts) == 0:
            break  # no more posts returned
        for post in posts:
            all_posts.append(post)

        offset = offset + increment

    return all_posts


def find_post(wp, identifier):
    for _post in get_posts(wp):
        if cust_field_dict(_post).get('identifier') == identifier:
            return _post

    return None

def get_site_names():
    """Return a list of al site names in the configuration"""
    config = get_config()

    if config is None:
        logger.error("No metatab configuration found. Can't get Wordpress credentials. Maybe create '~/.metapack.yaml'")

    return [k for k in config.get('wordpress', {})]


def get_site_config(site_name):
    config = get_config()

    if config is None:
        logger.error("No metatab configuration found. Can't get Wordpress credentials. Maybe create '~/.metapack.yaml'")

    site_config = config.get('wordpress', {}).get(site_name, {})

    if not site_config:
        logger.error("In config file '{}', expected 'wordpress.{}' section for site config"
                     .format(config['_loaded_from'], site_name))

    if 'url' not in site_config or 'user' not in site_config or 'password' not in site_config:
        logger.error(dedent(
            """
            Incomplete configuration. Expected:
                wordpress.{site_name}.url
                wordpress.{site_name}.user
                wordpress.{site_name}.password
            In configuration file '{cfg_file}'
            """.format(site_name=site_name, cfg_file=config['_loaded_from'])
        ))

    return site_config['url'], site_config['user'], site_config['password']


def prepare_image(slug, file_name, post_id):
    # prepare metadata
    data = {
        'name': 'picture.jpg',
        'type': 'image/jpeg',  # mimetype
    }

    # read the binary file and let the XMLRPC library encode it into base64
    with open(file_name, 'rb') as img:
        return {
            'name': '{}-{}'.format(slug, basename(file_name)),
            'type': 'image/png',  # mimetype
            'bits': xmlrpc_client.Binary(img.read()),
            'post_id': post_id
        }

def get_wp(site_name, output_file, resources, args):
    """

    """

    url, user, password = get_site_config(site_name)

    meta = {}
    for r in resources:
        if r.endswith('.json'):
            with open(r) as f:
                meta = json.load(f)

    fm = meta.get('frontmatter', {})

    if not 'identifier' in fm or not fm['identifier']:
        logger.error("Can't find a post that doesn't have a UUID. Publish it first.")

    wp = Client(url, user, password)

    return find_post(wp, fm['identifier'])


def publish_wp(site_name, output_file, resources, args):
    """Publish a notebook to a wordpress post, using Gutenberg blocks.

    Here is what the metadata looks like, in a section of the notebook tagged 'frontmatter'

    show_input: hide
    github: https://github.com/sandiegodata/notebooks/blob/master/tutorial/American%20Community%20Survey.ipynb
    identifier: 5c987397-a954-46ca-8743-bdcd7a71579c
    featured_image: 171
    authors:
    - email: eric@civicknowledge.com
      name: Eric Busboom
      organization: Civic Knowledge
      type: wrangler
    tags:
    - Tag1
    - Tag2
    categories:
    - Demographics
    - Tutorial

    'Featured_image' is an attachment id

    """
    import re

    url, user, password = get_site_config(site_name)

    meta = {}
    for r in resources:
        if r.endswith('.json'):
            with open(r) as f:
                meta = json.load(f)

    if not 'frontmatter' in meta:
        raise PublishException('No Frontmatter')

    fm = meta.get('frontmatter', {})

    if not 'identifier' in fm or not fm['identifier']:
        raise PublishException(
            "Can't publish notebook without a unique identifier. "
            "Add this to the Metatab document or frontmatter metadata:"
            "\n   identifier: {}".format(str(uuid4()))+
            "\n Or, run -F to create frontmatter" )

    wp = Client(url, user, password)

    post = find_post(wp, fm['identifier'])

    if post:
        logger.info("Updating old post")
    else:
        post = WordPressPost()
        post.id = wp.call(NewPost(post))
        logger.info(f"Creating new post; could not find identifier {fm['identifier']} ")

    post.title = fm.get('title', '')
    post.slug = fm.get('slug')

    with open(output_file) as f:
        content = f.read()

    post.terms_names = {
        'post_tag': fm.get('tags', []),
        'category': fm.get('categories', [])
    }

    if args.header:
        print(yaml.dump(fm, default_flow_style=False))

    set_custom_field(post, 'identifier', fm['identifier'])

    post.excerpt = fm.get('excerpt', fm.get('brief', fm.get('description')))

    def strip_image_name(n):
        """Strip off the version number from the media file"""
        from os.path import splitext
        import re
        return re.sub(r'\-\d+$', '', splitext(n)[0])

    extant_files = list(wp.call(GetMediaLibrary(dict(parent_id=post.id))))

    def find_extant_image(image_name):
        for img in extant_files:
            if strip_image_name(basename(img.metadata['file'])) == strip_image_name(image_name):
                return img

        return None

    for r in resources:

        image_data = prepare_image(fm['identifier'], r, post.id)
        img_from = "/{}/{}".format(fm['slug'], basename(r))

        extant_image = find_extant_image(image_data['name'])

        if extant_image:
            logger.info(f"Post already has image: {extant_image.id} {extant_image.link}")
            img_to = extant_image.link

        elif r.endswith('.png'):  # Foolishly assuming all images are PNGs
            if args.no_op:
                response = {
                    'id': None,
                    'link': 'http://example.com'
                }
            else:
                response = wp.call(UploadFile(image_data, overwrite=True))

            logger.info("Uploaded image {} to id={}, {}".format(basename(r), response['id'], response['link']))

            img_to = response['link']

        else:
            continue

        content = content.replace(img_from, img_to)



    if fm.get('featured_image') and str(fm.get('featured_image')).strip():
        post.thumbnail = int(fm['featured_image'])

    elif hasattr(post, 'thumbnail') and isinstance(post.thumbnail, dict):
        # The thumbnail expects an attachment id on EditPost, but returns a dict on GetPost
        post.thumbnail = post.thumbnail['attachment_id']

    content = re.sub(r'^\s*$', '', content)
    post.content = content


    if args.publish:
        post.post_status = 'publish'

    if not args.no_op:
        try:
            r = wp.call(EditPost(post.id, post))
        except Fault as e:
            if 'attachment' in str(e):  # Remove attachment and try again.
                post.thumbnail = None
                r = wp.call(EditPost(post.id, post))

        return r, wp.call(GetPost(post.id))
    else:
        return None, None
