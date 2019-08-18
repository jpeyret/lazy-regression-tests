# 🍰 Cake first! 🥒 Veggies later.

#### Let's run a failing test

`pytest test_urls_security_psroledefn.py::Test_List::test_it`

````
... snipped out...
E       <title>
E   -    Search Rolez  👈 ❌ TYPO ❌
E   ?               ^
E
E   +    Search Roles   ✅ what we actually want
E   ?               ^
... snipped out...
FAILED test_urls_security_psroledefn.py::Test_List::test_it - AssertionError: '<!DO[395 chars] Rolez\n  😧😧😧
````

Note:  old-school `unittests` are supported:  `python test_urls_security_psroledefn.py Test_List.test_it`

#### Now run a diff command to see what went wrong.


`ksdiff exp/test_urls_security_psroledefn.Test_List.test_it.html got/test_urls_security_psroledefn.Test_List.test_it.html` 

In this case, the left hand file is what this particular test was **expecting** and the right hand side  is what it **got**.  Notice how the file names match the python test file, test class and method.



![](docs/screenshots/01.different.png)

Looks like somebody fixed a typo and that's why the test is failing.  

Note:  this was using **Kaleidoscope** on macOS, but you could use gnu `diff` just as well.


#### 🍰 How to reset expectations.

We can use Kaleidcscope to tell Lazy to expect `Roles` rather than `Rolez`.  Save the `exp` file.

![](docs/screenshots/02.reset.png)

#### 🍰 and rerun the test, which now works.

````
pytest test_urls_security_psroledefn.py::Test_List::test_it
============================================================= test session starts =================
platform darwin -- Python 3.6.8, pytest-5.0.1, py-1.8.0, pluggy-0.12.0
rootdir: /Users/myuser/beemee
plugins: celery-4.3.0, cov-2.7.1
collected 1 item

test_urls_security_psroledefn.py .                                                          [100%]

========================================================== 1 passed in 4.73 seconds ===============

````

(btw, the 4.73 secondes isn't really Lazy's fault, this is my live test suite)


### The directory structure.

Lazy's required configuration includes 2 environment variables, `$lzrt_template_dirname_exp`, the **expectations** directory and `$lzrt_template_dirname_got`, the **received** / got directory.  `exp` and `got`, for short.

Each time a test is run, outputs are saved in `got` and compared to what stored in `exp`.  (No, those directories are not really side by side).  You don't really care what's in `got`, it gets rewritten each time.  The contents of `exp` are essentially a test spec however.


````
├── exp
│   └── test_urls_security_psroledefn 
│       └── test_urls_security_psroledefn.Test_List.test_it.html
└── got
    └── test_urls_security_psroledefn
        └── test_urls_security_psroledefn.Test_List.test_it.html
````

#### 🍰 The test method

**test_urls_security_psroledefn.py**:

````
class Test_List(Base):
	....

    def test_it(self):
    	""" get data from an url configured elsewhere """

		# this is test suite code and has nothing to do with Lazy
        response = self.get(self.T_URL_BASE)	
        self.assertEqual(response.status_code, 200)  #👈 you still need non-content tests!

		# 👇 That's pretty much it, as far as Lazy goes 🍰
		#    this is what formats the data, runs the assertion and saves outputs to the file system.
        self.lazychecks_html(response)  
		

````

#### 🍰 But... what's that Base class?

````

from <path>.customlazy import CustomGenericLazyMixin

class LazyMixin(CustomGenericLazyMixin):
	""" 
	This class needs to be copy-pasted into EACH `test_xxx.py` script
	as it tracks file system and module information from Python built-in variables
	this is what positions output in `exp` and `got` directories
	"""
	
	# 🍰 - always the same!
    lazy_filename = GenericLazyMixin.get_basename(__name__, __file__, __module__)



class Base(LazyMixin, unittest.TestCase):

	"""🍰 Lazy's lazycheck_xxx methods are directly available here, nothing to do."""

	def get(self, T_URL):
		.... whole buncha stuff relating to the test suite, like that `self.get(<url>)`

````

# 🥒🥒🥒 : Veggie time:  let's be honest, how much work is this?


There's quite a bit of upfront work you need to do on your base Custom class.  Some of it can be improved in future versions of Lazy.  But the filter functions will remain complex and you have to write them.  The good news is that you only need to do it once.

Basic **customlazy.py** example:

````

from lazy_regression_tests.core import (
    LazyMixin, RemoveTextFilter, CSSRemoveFilter 
)


class CustomGenericLazyMixin(LazyMixin):
	""" 
	🥒🥒🥒🥒 :-( There's work to do here... 
	"""

	#each extension expects to find a matching lazy_filter_xxxx
	lazy_filter_html = build_html_filter()

    def lazychecks_html(
        self, response, suffix=""
    ):
    	"""	
    	This is where you tell Lazy how to check html.
    	🥒🥒 This could be put in the core class, but it hasn't been done yet.
    	"""
        response = getattr(response, "content", None) or response
        res_html = self.assertLazy(
            response, "html", suffix=suffix
        )
        return res_html


def build_html_filter(onlyonce=False):

    """
    🥒🥒🥒🥒🥒
    unfortunately, diff-based regression tests requires you to strip out
    things that vary frequently.
    in Django that will be CSRF Token, even/odd <tr> CSS classes, timestamps....

    _You_ need to do this, using regex and Lazy's utility functions

    Here's a (simplified) example:
    """


    li_remove = [
        # the csrf token is by nature always changing.
        # security nonces, if used, will also need scrubbing
        re.compile("var\scsrfmiddlewaretoken\s=\s"),

        # This a Vue/Webpack production time bundling artefact...
        re.compile('<link type="text/css" href="/static/webpack/styles/'),

        # in my case, what I call usergroups need separate processing because they change as well
        # the CSSRemove filter will save what it finds in lazycheck_html's results, under `found.<hitname>`
        CSSRemoveFilter("#usergroup_table", hitname="usergroup_table"),
    ]

    res = RemoveTextFilter(li_remove)
    return res


````


# 🥒🥒🥒 DISCLAIMERS (more Veggies) 🥒🥒🥒

### The priority is code that works, **for me**.

I actively use Lazy in development and testing.  I've tried to keep full test coverage for what's uploaded to pypi.  And it really works.  But, at the same time, whenever I need something new I usually just dump into into my app's custom CustomGenericLazyMixin and get it working there.

If it looks as if it can be useful, I'll put in `lazy-regression-tests`, but might not write tests for it.  Example: `CSSRemoveFilter`.

Some of my custom functions really need to go back into the core, but they're only in the examples directory.  With things like `lazychecks_json` and `lazycheck_yaml`, they're often only in `lazy_regression_tests.examples.customlazy.CustomGenericLazyMixin`.

This is also why this write up and doc are ... light. 👇

#### 🥒🥒🥒TODO: 
- documenting the core classes
- type-hinting
- bit of refactoring 
- add Python 2.7 support 
    - 2.7-capable test code is especially important now
- better support for unittest *and* pytest command lines



### 🥒🥒 You need to manage `diff` launches yourself.

The sample contains a template bash shell to launch the appropriate diff but getting something like that working is very much customization territory.  `find -cmin -5` or the like, in the `got` directory , can help you, but the general idea is you want to manage one error at a time with `pytest -x` or `unitest -f` switches.


### 🥒🥒🥒🥒 Stripping out transient and variable output is hard!

- I've used diffing for a looong time.  The biggest barrier is avoiding constant comparison exceptions from
data that is expected to change.  That's what the filter utilities are for, but you still need to tweak
**your** outputs.  Some classic gotchas:

	- timestamps
	- CSRF protection tokens
	- ORM auto-generated `id` keys
	- Webpack resource hashes
	- randomnly-ordered data

- Related to that is the notion of formatters.  I run all my html through `BeautifulSoup.prettify()`.  Big
huge chunks of text with haphazardly located newlines **will** bite you.

- **You** need to sort data, even if your application doesn't care.  Get into the habit of adding `ORDER BY ` to your 
queries.


### Some features work, but with messy code that I haven't adjusted yet.

For example, Lazy has the notion of directives and is supposed to get them from the command line and environment variables.
In practice, I now only use the environment variables so the command line handling code is crufty.  I'm still using both regular `unittest` and `pytest` so command line switches are an extra-sore point.

The core structure was written up very quickly, over about 2 days.  Some of the design choices are quite crufty in hindsight.  

### You still need to write validation checks

That `self.assertEqual(response.status_code, 200)` was necessary because, **if your code breaks and starts returning 404s the last you want to do is telling Lazy that the warning page presented to the end user is now the expected behavior.**



# 🍰🍰🍰 Extra features


### Directives

environment variable `$lzrt_directive` can be used to manipulate lazy's behavior.  For example, if you've modified your templating system
and all output is expected to change, then set `$lzrt_directive=baseline`.  Lazy will report errors, but continue without failing the tests 
**and** it will copy all received data to their match `exp` files.  Use it when you know it's appropriate and don't forget to reset it **immediately** afterwards.

### SQL?  JSON?

Yup.  `self.lazychecks_sql(got)`  Watch your ORM code, for example.  

a formatter for sql can be as simple as:

````
def format_sql(sql: str, *args, **kwds) -> str:
    """linefeed on commas and strip out empty lines"""

    sql = sql.replace(",", "\n,")
    li = [line.lstrip() for line in sql.split("\n") if line.strip()]
    return "\n".join(li)

````

giving:

````
insert into bme_c_pspnlgrpdefn ( rdbname 
, market 
, actions 
, descr 
````

JSON?: `self.lazychecks_json({"some" : "data"}})`


### Complex composable objects?

I've had *some* success taking arbitrary objects or dictionaries, pushing them through a `yaml.dump` and comparing them.  

Let's say you a OrderProcessor object that gets composed from a reportStrategy object and a saveStrategy object.

Just `self.lazycheck_yaml(order_processor_instance)`.

#### Gotchas? 

- handling un-pickable and custom objects and attributes
	-Yaml dump is better at custom objects.
- any variable attribute like a `OrderProcessor.todaysDate` variable.


## P.S.  Not really a big 🍰 lover and I am OK with 🥒 ;-)