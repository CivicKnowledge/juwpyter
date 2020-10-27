
import mimetypes
import os
import shutil
from genericpath import exists
from os import makedirs
from os.path import join


# From http://stackoverflow.com/a/295466
def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import re
    import unicodedata
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('utf8').strip().lower()
    value = re.sub(r'[^\w\s\-\.]', '', value)
    value = re.sub(r'[-\s]+', '-', value)
    return value


def ensure_dir(path):
    if path and not exists(path):
        makedirs(path)
