"""docstring"""
import unittest
import sys
import os
import logging
import argparse

import glob
import re

logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


from lib.utils import debugObject, ppp, Dummy, set_cpdb, set_rpdb

from importlib import import_module

# from django.utils.module_loading import import_string


from traceback import print_exc as xp
import pdb


def cpdb():
    return cpdb.enabled


cpdb.enabled = False


def rpdb():
    return rpdb.enabled


rpdb.enabled = False

if __name__ == "__main__":
    set_cpdb(cpdb, remove=True)
    set_rpdb(rpdb, remove=True)


class MainManager(object):
    """ manages batch"""

    di_opt = {}

    def __init__(self, options):

        try:
            self.options = options

            msg = debugObject(self, "\n\n MainManager.__init__:end")
            msg += debugObject(self.options, "\noptions")

            func_filter_factory = import_string(self.options.filter_builder)
            self.filter = func_filter_factory()



            logging.info(msg)
            print(msg)


        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
            raise

    def process(self):
        try:

            if self.options.fnp_i and os.path.isfile(self.options.fnp_i):
                self.reformat(self.options.fnp_i)
            else:
                raise NotImplementedError()
        except (Exception,) as e:
            ppp(self, self)
            ppp(self.options, "options")
            if cpdb(): 
                pdb.set_trace()
            raise


    def reformat(self, fnp_i):
        try:

            with open(fnp_i) as fi:
                lines = fi.readlines()
            raise NotImplementedError()
        except (Exception,) as e:
            if cpdb(): pdb.set_trace()
            raise

    @classmethod
    def getOptParser(cls):

        parser = argparse.ArgumentParser()

        dest = "filter_builder"
        parser.add_argument(
            dest=dest,
            action="store",  # store_true, store_false
            help="python import path to a function returning a lazy_regression_tests.utils.KeepTextFilter/RemoveTextFilter",
        )

        dest = "fnp_i"
        parser.add_argument(
            dest=dest,
            action="store",  # store_true, store_false
            help="%s dump file needing formatting" % (dest),
        )

        return parser


########################
# shamelessly copied from django.utils.module_loading
########################


def import_string(dotted_path):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """

    try:

        try:
            module_path, class_name = dotted_path.rsplit(".", 1)
        except ValueError:
            msg = "%s doesn't look like a module path" % dotted_path
            raise ImportError

        module = import_module(module_path)

        try:
            return getattr(module, class_name)
        except AttributeError:
            msg = 'Module "%s" does not define a "%s" attribute/class' % (
                module_path,
                class_name,
            )
            raise ImportError

    except (Exception,) as e:

        if cpdb(): 
            ppp(locals(),"\nlocals")
            print("sys.path:")
            for pa in sys.path:
                print(pa)

            pdb.set_trace()
        raise


if __name__ == "__main__":

    parser = MainManager.getOptParser()
    options = parser.parse_args()
    mgr = MainManager(options)
    mgr.process()
