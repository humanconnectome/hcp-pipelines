#!/usr/bin/env python3

# import of built-in modules
import inspect

# import of third party modules
# None

# import of local modules
# None

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2017, The Human Connectome Project"
__maintainer__ = "Timothy B. Brown"

def get_name():
    return inspect.stack()[1][3]
