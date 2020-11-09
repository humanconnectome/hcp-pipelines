#!/usr/bin/env python3

"""str_utils.py: Some simple and hopefully useful string utilities."""

# import of built-in modules
import os
import urllib.parse

# import of third party modules
# None

# import of local modules
# None

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2016, The Human Connectome Project"
__maintainer__ = "Timothy B. Brown"


def remove_ending_new_lines(input_str):
    """Remove a new line characters from the end of the supplied string if any are there."""
    line = input_str
    while line != '' and os.linesep == line[-1]:
        line = line[:-1]

    return line


def get_server_name(url):
    (scheme, location, path, params, query, fragment) = urllib.parse.urlparse(url)
    if location == '':
        return url
    else:
        return location
