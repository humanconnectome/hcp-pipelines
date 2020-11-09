#!/usr/bin/env python3

"""os_utils.py: Some simple and hopefully useful os utilities."""

# import of built-in modules
import glob
import logging
import os
import shutil
import tempfile

# import of third party modules
# None

# import of local modules
# None

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2016, The Human Connectome Project"
__maintainer__ = "Timothy B. Brown"


# create and configure a module logger
log = logging.getLogger(__file__)
# log.setLevel(logging.WARNING)
log.setLevel(logging.INFO)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(name)s: %(message)s'))
log.addHandler(sh)


def getenv_required(var_name):
    value = os.getenv(var_name)
    if not value:
        raise ValueError("Environment variable " + var_name + " is required, but is not set!")
    return value


def lndir(src, dst, show_log=False, ignore_existing_dst_files=False):

    if not os.path.isdir(src):
        raise OSError("ERROR: %s is not a valid directory." % src)

    if not os.path.isdir(dst) and os.path.exists(dst):
        raise OSError("ERROR: %s exists but is not a valid directory." % dst)

    if not os.path.exists(dst):
        os.mkdir(dst)

    for root, dirs, files in os.walk(src):
        log.debug("root:  " + root)

        for filename in files:
            log.debug("filename: " + filename)
            try:
                src_filename = '%s/%s' % (root, filename)
                dst_filename = '%s%s/%s' % (dst, root.replace(src, ''), filename)
                if show_log:
                    print("linking: %s --> %s" % (dst_filename, src_filename))
                os.symlink(src_filename, dst_filename)

            except FileExistsError as e:
                if not ignore_existing_dst_files:
                    raise e

        for dirname in dirs:
            log.debug("dirname: " + dirname)
            try:
                os.mkdir('%s%s/%s' % (dst, root.replace(src, ''), dirname))
            except OSError:
                pass


def replace_lndir_symlinks(srcpath):
    """
    Replaces all symlinks in an lndir (see above) created directory structure with
    copies of the files that are linked to.
    """
    for filename in glob.glob(srcpath + os.sep + '*'):
        log.debug("filename: " + filename)

        if os.path.isdir(filename) and not os.path.islink(filename):
            log.debug("\tis a directory that is not a symlink - recursing")
            replace_lndir_symlinks(filename)

        elif os.path.isfile(filename) and os.path.islink(filename):
            log.debug("\tis a regular file that is a symlink and should be replaced")

            log.info("Replacing: " + filename + " with copy of: " + os.path.realpath(filename))

            with tempfile.TemporaryDirectory() as temp_dirpath:
                temp_filename = temp_dirpath + os.sep + os.path.basename(filename)
                shutil.copy2(filename, temp_filename)
                os.remove(filename)
                shutil.move(temp_filename, filename)

def replace_symlinks_with_relative(srcpath):

    for filename in glob.glob(srcpath + os.sep + '*'):

        fullpath = os.path.abspath(filename)

        if os.path.islink(fullpath):
            linked_to = os.path.realpath(fullpath)
            relative_path = os.path.relpath(linked_to, os.path.dirname(fullpath))
            os.remove(fullpath)
            print(fullpath + " -> " + relative_path)
            os.symlink(relative_path, fullpath)

        if os.path.isdir(fullpath):
            replace_symlinks_with_relative(fullpath)


if __name__ == "__main__":
    lndir('/home/HCPpipeline/usr', '/home/HCPpipeline/usr1', show_log=True, ignore_existing_dst_files=True)
