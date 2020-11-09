#!/usr/bin/env python3

# import of built-in modules
import sys
import argparse

# import of third-party modules
# None

# import of local modules
# None

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2016, The Human Connectome Project"
__maintainer__ = "Timothy B. Brown"


class MyArgumentParser(argparse.ArgumentParser):
    """This subclass of ArgumentParser prints out the help message when an error is found in parsing."""

    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)
