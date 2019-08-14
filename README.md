### GOAL:  test with as little effort as possible.

let's say I have test that can be run like this `pytest`

- `pytest test_urls_security_psroledefn.py::Test_Detail::test_404`

and yesterday, when I last ran it, it got me this output:

````
PASSED test_urls_security_psroledefn.py::Test_Detail::test_404
========================================================== 1 passed in 3.98 seconds 
````


Now, this is pretty much a standard Django unit test, calls an URL, checks the returned html.

However, today someone noticed a typo in the page title and fixed it.   Should be `Roles` instead of `Rolez`.


Now, I haven't the test since yesterday, when it passed

But let's say that I navigate to a directory indicated by environment variable 
`$lzrt_template_dirname_exp`, whatever I've set that to.

Now I open file `test_urls_security_psroledefn.Test_Detail.test_404.html`.  I don't have to at this point, I am not going to modify anything, this is just to introduce the notion of **expectations**.

This is my last recorded and approved **expectation** file.  That's what my test expects the prettified html returned by Django for this test's url to look like (**each bit of data you want to regression-test gets its own file**).


**test_urls_security_psroledefn.Test_Detail.test_404.html**:

````
<!DOCTYPE html>
<html lang="en">
 <head>
  <meta charset="utf-8"/>                          
  <meta content="width=device-width, initial-scale=1" name="viewport"/>
  <title>
   Search Rolez   👈 ❌ TYPO ❌
  </title>

````

OK, let's run the test again, with the modified code.  Bad news:

````
FAILED test_urls_security_psroledefn.py::Test_Detail::test_404 - AssertionError: '<!DO[395 chars] Rolez\n  </title>\n  <link href="/static/w...
========================================================== 1 failed in 3.87 seconds ===========================================================

````

Now, guess what, there is a flip dictory `$lzrt_template_dirname_got` that holds received test output.

And when I find **test_urls_security_psroledefn.Test_Detail.test_404.html** in that directory and diff both files visually, I see the reason for the failure.

![](./docs/screenshots/001.diff_Rolez.png)

So, do I modify my test code?  No need to.  Let's use Kaleidoscope, the diff utility I am using, to copy the right hand side to the left hand side.  Copy the got-ten file contents to the exp-ected side.

![](/Users/jluc/kds2/mygithub/lazy-regression-tests/lazy_regression_tests/docs/screenshots/002.copied_Roles.png)

And re-run the test, via `pytest test_urls_security_psroledefn.py::Test_Detail::test_404`:

````
PASSED test_urls_security_psroledefn.py::Test_Detail::test_404
========================================================== 1 passed in 3.95 seconds ===========================================================
````

The **exp** file matched the **got** (received) file and so the lazy tester is happy.


### And how complicated is actual test code?

````
class LazyMixin(GenericLazyMixin):
	 """you need a Mixin class in each module to track file system info"""
	 
	 # 👇 this gives the LazyMixin sufficient info about the Python file's location
    lazy_filename = GenericLazyMixin.get_basename(__name__, __file__, __module__)

class Base(LazyMixin, unittest.TestCase):
    """this is some household base test class that holds common behavior for the test classes
    """

class Test_Detail(Base):
	"""This class, besides being a TestCase and having behavior from Base, is also a LazyMixin"""
	
	def test_404(self):
		"""sustantially, if you ignore the self.get the only thing you need is the 2nd line"""
		response = self.get("/Roles/test404")
		self.assertEqual(404, response.status_code)
		self.lazychecks_html(response.content)   #👈 this is what drives lazychecks
````

the lazychecks_html will examine the test class name, the method name, combine that with `lazy_filename` you've set above.  Combine that with `$lzrt_template_dirname_exp` and `$lzrt_template_dirname_got`, it knows both where to save the received data, in the **got** directory, as well as where the **exp** file is.  Oh, and since it's an *html* lazy check, it pass the response.content through `BeautifulSoup.prettify()`.

When it received `Roles` among the other response content, that did not match the expected `Rolez`.  So you got an error.  By using the diff utility to copy that 1 mismatched line into the expectations file, you've insured that `Roles` is now expected.  Which is why the test passed the 2nd time.

There's more to it. GenericLazyMixin actually is a subclass that I wrote once for this site.  It subclasses the class in this module.  Yay, more stuff to write, you say.

Well, there's one very good reason for a site-level customization.

````
from lazy_regression_tests.core import LazyMixin
class GenericLazyMixin(LazyMixin, Defaults):

	def build_html_filter(onlyonce=False):
	    # filter out annotation comments
	    
        annotation_comments = "<!--\s*@anno",
	    li_remove = [
	        re.compile("var\scsrfmiddlewaretoken\s=\s"),
	        re.compile('\scsrfmiddlewaretoken="'),
	        re.compile("var\scsrf_token\s")
		    CSSRemoveFilter("#usergroup_table", hitname="usergroup_table"),
	    ]

	    res = RemoveTextFilter(li_remove)
	    return res

````

This strips out both contents that for some reason I don't want to diff from run to run (the `CSSRemoveFilter`), as well contents which Django **guarantees** will change, like its **CSRF Token**.

The CSSRemoverFilter has an optional `hitname` variable, which is where BeautifulSoup's CSS selector will deposit what it found, before snipping it out of the response.  You can write your own validation code for that element.

### SQL Data:

OK, what about SQL that gets generated somewhere, perhaps your ORM?  Yup, looks like `self.lazychecks_sql(got)`.

### JSON:

`self.lazychecks_json(di_received)`  In this case, di_received is actually a `dict` since json data is pretty much dict as far as Python cares.

### Formatters and filters:

Both those types have their custom filters and formatters, looking like:

````
def format_sql(sql: str, *args, **kwds) -> str:
    """makes diff-ing easier"""

    sql = sql.replace(",", "\n,")
    li = [line.lstrip() for line in sql.split("\n") if line.strip()]
    return "\n".join(li)


def format_json(dict_, filter=None):
    return str(
        json.dumps(dict_, sort_keys=True, indent=4, separators=(",", ":"))
    ).strip()
````

This is a really, really, hastily written up README, but that's the basic idea.  The one big caveat is that it does not mean you can skip deeper tests.  The reason I have `self.assertEqual(404, response.status_code)` in addition is that lazycheck will accept what you tell it are the expectations.

If the 404 URL you are testing suddenly finds some random data and returns it with a 200 status, you could, by mistake, tell lazy to expect that from now on.  Now, your actual program is expecting a 404, but if you weren't performing your own checks you'd never hear a peep from lazy checking, it's now happy with the random data.

At least until it changes.  lazy checking will flag any changes to any received data that is not filtered out.  That's its only purpose.

