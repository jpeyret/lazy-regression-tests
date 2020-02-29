=====
Usage
=====

Configure environmental variable::

    $lzrt_template_dirname_exp : where do you save expectations files
    $lzrt_template_dirname_got : where is got/received data stored, in files.

To use Lazy Regression Tests in a project::

    
    from lazy_regression_tests.lazy3 import LazyMixin
    from lazy_regression_tests.lazy3.filters import JsonFilterManager

    class LazyMixinBasic(LazyMixin):
        """ base Mixin class for the lazy test framework """

        # tracks filenames to use for each test
        lazy_filename = LazyMixin.get_basename(__name__, __file__, __module__)


    class Test_JSON_Data(LazyMixinBasic, unittest.TestCase):
        """ check that a, JSON-dumpable, dictionary is 
        always the same
        """

        cls_filters = dict(json=JsonFilterManager())

        def test_it(self):
            """ simulate data changes """
            try:

                #your test stuff
                data = my_test_function_that_returns_a_dictionary()

                #this will check that `data` is always the same on each run
                self.assert_exp(data, "json")  

            except (Exception,) as e:
                raise

