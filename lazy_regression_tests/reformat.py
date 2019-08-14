"""docstring"""
import unittest
import sys
import os
import logging
import argparse
import codecs
import hashlib

import glob
import re

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


from lazy_regression_tests._baseutils import debugObject, ppp, Dummy, set_cpdb, set_rpdb


from importlib import import_module

from traceback import print_exc as xp
import pdb


def cpdb():
    return cpdb.enabled


cpdb.enabled = False  # type: ignore


def rpdb():  # pragma : no cover
    return rpdb.enabled


rpdb.enabled = False  # type: ignore
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

            self.func_filter_factory = import_string(self.options.filter_builder)
            self.filter_ = self.func_filter_factory(onlyonce=True)

            if self.options.output_dir and not os.path.isdir(self.options.output_dir):
                raise ValueError(
                    "output_dir:%s does not exist" % (self.options.output_dir)
                )

            logging.info(msg)
            print(msg)

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def process_input_directory(self, dir_in):
        try:
            globmask = getattr(self.func_filter_factory, "globmask", "*")

            li = glob.glob(os.path.join(dir_in, globmask))
            for fnp in li:
                self.reformat(fnp)

            if not self.options.write:
                raise NotImplementedError(
                    "need to implement output_dir on input dir.  for now only write-in-place is supported"
                )
        except (Exception,) as e:  # pragma : no cover
            print("\n\nli (first 5):")
            for fnp in li[0:5]:
                print(fnp)

            if cpdb():
                pdb.set_trace()
            raise

    def process(self):
        try:

            if self.options.input_ and os.path.isfile(self.options.input_):
                self.reformat(self.options.input_)
            elif self.options.input_ and os.path.isdir(self.options.input_):
                self.process_input_directory(self.options.input_)
            else:
                raise NotImplementedError()
        except (Exception,) as e:  # pragma : no cover
            ppp(self, self)
            ppp(self.options, "options")
            if cpdb():
                pdb.set_trace()
            raise

    def _hash(self, data):
        h = hashlib.sha1()
        try:
            h.update(data)
        except (UnicodeEncodeError,) as e:
            return None
        return h.digest()

    def reformat(self, fnp_i):
        try:

            with codecs.open(fnp_i, encoding="utf-8", errors="ignore") as fi:
                previous = fi.read()

            h_previous = self._hash(previous)

            refiltered = self.filter_(previous)

            h_refiltered = self._hash(refiltered)
            if h_previous is not None and h_previous == h_refiltered:
                logger.info("no changes for %s" % (fnp_i))
                return

            if self.options.output_dir:
                basename = os.path.basename(fnp_i)
                fnp_o = os.path.join(self.options.output_dir, basename)

                logger.info("\ndiff %s %s" % (fnp_i, fnp_o))
            else:
                fnp_o = fnp_i

            with codecs.open(fnp_o, encoding="utf-8", errors="ignore", mode="w") as fo:
                fo.write(refiltered)

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
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

        dest = "input_"
        parser.add_argument(
            dest=dest,
            action="store",  # store_true, store_false
            help="%s dump file needing formatting" % (dest),
        )

        dest = "output_dir"
        parser.add_argument(
            "--" + dest,
            action="store",  # store_true, store_false
            help="%s output directory, if not in-place" % (dest),
        )

        dest = "write"
        default = False
        # choices=["a","b","c"]
        parser.add_argument(
            "--" + dest,
            default=default,
            action="store_true",
            help="%s [%s]" % (dest, default),
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

    except (Exception,) as e:  # pragma : no cover

        if cpdb():
            ppp(locals(), "\nlocals")
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
