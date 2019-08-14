#######################################################
# This is an extract of the actual usage of LazyMixin
# for a given user application.
# Sample is incomplete as it is extracted out of the
# main codeline
# but it should give an idea
#######################################################


from lazy_regression_tests.core import (
    LazyMixin,
    DiffFormatter,
    lazy_baseline,
    lazy_ignore as _lazy_ignore,
    lazy_pass_missing,
    lazy_nodiff as _lazy_nodiff,
)


def lazy_ignore(LazyMixin):
    _lazy_ignore(LazyMixin)
    _lazy_nodiff(LazyMixin)


from lazy_regression_tests.utils import (
    DictionaryKeyFilter,
    RemoveTextFilter,
    RegexRemoveSaver,
    RegexSubstitHardcoded,
    RegexSubstitFilter,
    curry_func,
    simple_subber,
)

from lazy_regression_tests.filters import CSSRemoveFilter

import pdb


def cpdb():
    return cpdb.enabled


cpdb.enabled = False  # type: ignore


def rpdb():  # pragma : no cover
    return rpdb.enabled


rpdb.enabled = False  # type: ignore
settings_hitname = "settings"
patre_settings = re.compile("var\ssettings\s=\s")


def format_sql(sql: str, *args, **kwds) -> str:
    """makes diff-ing easier"""

    sql = sql.replace(",", "\n,")

    li = [line.lstrip() for line in sql.split("\n") if line.strip()]

    return "\n".join(li)


def build_html_filter(onlyonce=False):

    """ you can use this via reformat to remodify already-captured data
    ex:
    python reformat.py tests.lazycheck.build_html_filter <your expectations directory or a specific file> --write

    """

    tr_odd_even = RegexSubstitHardcoded(
        '<tr\sclass="(even|odd)', '<tr class="even_odd">'
    )

    replacement = "even_odd"

    # `curry_func` is needed because regex.sub can call a function but that function only takes 1 variable, the
    # the regex match.  So replacement is pre-populated.

    sub_evenodd = curry_func(
        # besides verbose, the curry-func can pass on other optional keyswords to the subber
        # `rpdb` being a useful one
        simple_subber,
        replacement=replacement,
        onlyonce=onlyonce,
    )

    #################################
    # usergroup ids change after each `Batch.build_usergroup`
    #################################

    sub_usergroup_ids = RegexSubstitFilter(
        "security/usergroups/(\d+)/",
        curry_func(simple_subber, replacement="#usergroup_id", verbose=verbose),
    )

    sub_usergroup_tagtextdigits = RegexSubstitFilter(
        '\s{0,1}lzrt-sub-textdigits\s{0,1}.*".*>(\d+)',
        curry_func(simple_subber, replacement="#usergroup_id", verbose=verbose),
    )

    # filter out annotation comments
    annotation_comments = "<!--\s*@anno"

    # this is probably not working because of multiline aspects....
    # solution is either to move to a beautifulsoup type removal.
    # cant use comments.  GRRRR
    sub_tagtext = RegexSubstitFilter(
        '\s{0,1}lzrt-sub-tagtext\s{0,1}.*".*>[^<]+',
        curry_func(simple_subber, replacement="lazy:sub_tagtext.", verbose=verbose),
    )

    ###############
    # strip out variations on JS sources depending on webpack dev/production settings
    #    http://127.0.0.1:8001/static/webpack/pssecurity/detail.psroledefn.js
    #    http://localhost:3000/static_src/bundles/pssecurity/detail.psroledefn.js
    ###############
    sub_usergroup_jssrc0 = RegexSubstitFilter(
        '<script type="text/javascript" src="(/static/webpack)/',
        curry_func(simple_subber, replacement="_", verbose=verbose),
    )

    sub_usergroup_jssrc1 = RegexSubstitFilter(
        '<script type="text/javascript" src="(/static)/',
        curry_func(simple_subber, replacement="_", verbose=verbose),
    )

    sub_usergroup_jssrc2 = RegexSubstitFilter(
        'src="(http://localhost:3000/static_src/bundles)/',
        curry_func(simple_subber, replacement="_", verbose=verbose),
    )
    ################################################################

    # simple regexes carry out whole-line removal
    # specialized classes and function can modify line contents

    li_remove = [
        #!!!TODO!!!49.lazy/07.p3.RemoveResulter
        # take out the `settings` object as it needs to be assessed as a json-based
        # dictionary
        RegexRemoveSaver("var\ssettings\s=\s", hitname=settings_hitname),
        # the csrf token is by nature always changing.
        # nonces, if used, will also need scrubbing
        re.compile("var\scsrfmiddlewaretoken\s=\s"),
        re.compile("var\scsrf_token\s=\s"),
        re.compile('\scsrfmiddlewaretoken="'),
        re.compile("var\scsrf_token\s"),
        # This a Vue/Webpack production time bundling artefact...
        # <link type="text/css" href="/static/webpack/styles/pssystem/data.css" rel="stylesheet" />
        re.compile('<link type="text/css" href="/static/webpack/styles/'),
        # scrub out even/odd django cycling table styling
        RegexSubstitFilter('<tr\sclass="(even|odd)', sub_evenodd),
        annotation_comments,
        sub_usergroup_ids,
        sub_tagtext,
        sub_usergroup_tagtextdigits,
        # see their definition for info
        sub_usergroup_jssrc0,
        sub_usergroup_jssrc1,
        sub_usergroup_jssrc2,
        CSSRemoveFilter("#bmeRemotedatabases"),
        # usergroups needs separate processing to handle ordering changes from nicknames
        CSSRemoveFilter("#usergroup_table", hitname="usergroup_table"),
    ]

    res = RemoveTextFilter(li_remove)
    return res


# used to limit lazy reformat.py scopes - this function only ever applies to htmls...
build_html_filter.globmask = "*.html"


def build_json_filter(onlyonce=False, cls_=None):

    #            "task_id":"753a058a-640b-4842-a575-7b83cfd0d319",

    if cls_ is None:
        cls_ = Defaults

    def get_simpledictkeyfilter(keyname, replacement="..."):
        subber = RegexSubstitFilter(
            '"%s":"([^"]+)"' % (keyname),
            curry_func(simple_subber, replacement=replacement, verbose=verbose),
        )
        return subber

    li_remove = getattr(cls_, "ignore_attributes_json_response", [])
    li_subber = [get_simpledictkeyfilter(key) for key in li_remove]

    res = RemoveTextFilter(li_subber)
    return res


build_json_filter.globmask = "*.json"


class Defaults(object):
    # these attributes will be stripped out of the data dumps
    ignore_attributes_json_response = ["task_id", "li_rdbname", "LASTUPDDTTM"]


from yaml import dump as ydump


def yaml_formatter(got, *args, **kwds):
    try:

        result = ydump([got])
        return result
    except (Exception,) as e:  # pragma : no cover
        if cpdb():
            pdb.set_trace()
        raise


class GenericLazyMixin(LazyMixin, Defaults):
    @classmethod
    def get_basename(cls, name_, file_, module_):

        lazy_filename = os.path.splitext(os.path.basename(file_))[0]

        return lazy_filename

    lazy_filter_html = build_html_filter()

    lazy_filter_json = build_json_filter()

    lazy_message_formatter = DiffFormatter(window=2, maxlines=200)

    dict_keys_to_remove = ["li_rdbname", "LASTUPDDTTM"]

    #!!!TODO!!! hook this up to new build_json_filter
    dictfilter = DictionaryKeyFilter(dict_keys_to_remove)

    lazy_dirname_extras = "rdbname"

    # patre_settings = patre_settings

    _di_setting = UNDEFINED

    @property
    def di_setting(self):
        if self._di_setting is UNDEFINED:
            self.find_lazy_settings()

        return self._di_setting

    def debug_dump_yaml(self, obj, suffix="", msg=""):
        try:
            fnp0 = self.lazy_fnp_exp_root()
            if suffix and not suffix.startswith("."):
                suffix = ".%s" % (suffix)

            fn = "%s%s.yaml" % (os.path.basename(fnp0), suffix)
            fnp = os.path.join(constants.BME_APPLOGDIR, fn)

            with open(fnp, "w") as fo:
                fo.write(ydump(obj))

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def find_lazy_settings(self):

        try:
            self._di_setting = None

            #!!!TODO!!!49.lazy/07.p3.RemoveResulter should be used to simplify this
            # for found in self.lazytemp.filterhits:
            #     if self.patre_settings.search(found.found):
            #         self.li_setting.append(found.found)
            lazytemp = getattr(self, "lazytemp", None)
            if not lazytemp:
                #
                logger.error(
                    "%stest configuration error: settings can only be accessed after lazychecks_html%s"
                    % (logger_header, logger_footer)
                )
                return

            li_hits = self.lazytemp.filterhits.get(settings_hitname, [])
            if not li_hits:
                return

            contents = li_hits[0].found.strip()
            assert contents.startswith("var settings")

            _, settings = contents.split("=", maxsplit=1)

            settings = settings.rstrip(";")

            self._di_setting = json.loads(settings)

            self.di_setting_raw = self._di_setting.copy()

            self.dictfilter.scan(self._di_setting)

            return self._di_setting

        except (Exception,) as e:  # pragma : no cover

            if cpdb():
                pdb.set_trace()
            raise

    def get_usergroups_table_html(self, lazytemp=None):

        lazytemp = lazytemp or getattr(self, "lazytemp", None)
        if lazytemp is None:
            return None

        # howto- usergroup isolation as per 038.security.089.testing.p3.stable_tests_usergroups
        try:
            lazytemp_html = getattr(lazytemp, "res_html", lazytemp)
            usergroups_html = first(lazytemp_html.filterhits.get("usergroup_table", []))
        except (Exception,) as e:  # pragma: no cover
            if cpdb():
                pdb.set_trace()
            return None
        return usergroups_html

    def lazychecks_html(
        self, response, check_settings=True, no_assert=False, suffix=""
    ):
        try:
            # if rpdb(): pdb.set_trace()
            response = getattr(response, "response_content", None) or response
            res_html = self.assertLazy(
                response, "html", no_assert=no_assert, suffix=suffix
            )

            if check_settings:
                #!!!TODO!!!49.lazy/07.p3.RemoveResulter
                self.find_lazy_settings()
                self.lazytemp = res_json = self.assertLazy(
                    self.di_setting, "json", suffix=suffix
                )
                res_json.res_html = res_html
                return res_json

            else:
                self.lazytemp = res_html
                return res_html

        except (AssertionError,) as e:
            verbose = getattr(self, "verbose", None)
            if verbose:
                logger.info("fnp_exp:%s" % (self.lazytemp.fnp_exp))
                logger.info("fnp_got:%s" % (self.lazytemp.fnp_got))
            raise

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def lazychecks_jsonresponse(
        self, response, check_settings=True, no_assert=False, suffix=""
    ):

        funcname = "lazychecks_jsonresponse"

        try:
            if not isinstance(response, django.http.response.JsonResponse):
                logger.info("%s.not JsonResponse.#1" % (funcname))
                response2 = getattr(response, "_response", None)

                if isinstance(response2, django.http.response.JsonResponse):
                    response = response2
                else:
                    logger.info("%s.not JsonResponse.#2" % (funcname))

            if not isinstance(response, django.http.response.JsonResponse):
                logger.info("%s.not JsonResponse.#3" % (funcname))

                raise TypeError("%s. unsupported type:%s" % (funcname, type(response)))

            data = dict(vars(response))

            if "_container" in data:

                data["_container"] = [
                    json.loads(i.decode("utf-8")) for i in data["_container"]
                ]

            for key in ["_closable_objects", "client", "request", "json"]:
                _ = data.pop(key, None)

            for key in ["wsgi_request", "resolver_match"]:
                logger.info("  forcing %s to str" % (key))
                data[key] = str(data.get(key))

            # pdb.set_trace()

            try:
                test = json.dumps(data, sort_keys=True, indent=4, separators=(",", ":"))
            except (Exception,) as e:  # pragma : no cover
                for k, v in data.items():
                    logger.info("dumping %s" % (k))
                    json.dumps(dict(k=v))
                raise

            res = self.assertLazy(data, "json", no_assert=no_assert, suffix=suffix)

            # ppp(self.lazytemp.got["_container"][0])

            self.j_response = self.lazytemp.got.get("_container", [None])[0]

            return res

        except (AssertionError,) as e:
            verbose = 1 or getattr(self, "verbose", None)
            if verbose and self.lazytemp:
                fnp_exp = getattr(self.lazytemp, "fnp_exp", None)
                logger.info("fnp_exp:%s" % (fnp_exp))
                fnp_got = getattr(self.lazytemp, "fnp_got", None)
                logger.info("fnp_got:%s" % (fnp_got))
            raise

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def lazychecks_sql(self, sql, suffix=None):
        return self.assertLazy(sql, "sql", suffix=suffix, formatter=format_sql)

    def lazycheck_yaml(self, data, suffix=None, formatter=None):
        try:
            formatter = formatter or yaml_formatter
            return self.assertLazy(data, "yaml", suffix=suffix, formatter=formatter)
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def lazycheck_dump(self, data, suffix=None):
        try:
            return self.assertLazy(data, "txt", suffix=suffix)
        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def lazychecks_json(self, response, check_settings=True, suffix=""):
        try:

            try:
                # bit of a hack
                self.assertTrue("json" in response.content_type)
            except (AttributeError,) as e:
                pass

            response = getattr(response, "response_content", None) or response

            return self.assertLazy(response, "json", suffix=suffix)

        except (AssertionError,) as e:
            verbose = 1 or getattr(self, "verbose", None)
            if verbose:
                try:
                    logger.info("fnp_exp:%s" % (self.lazytemp.fnp_exp))
                    logger.info("fnp_got:%s" % (self.lazytemp.fnp_got))
                except (Exception,) as e:  # pragma : no cover
                    pass
            raise

        except (Exception,) as e:  # pragma : no cover
            if cpdb():
                pdb.set_trace()
            raise

    def check_sql(self, di_sql):
        try:
            sql = None
            for suffix, sql_ori in di_sql.items():
                sql = format_sql(sql_ori)
                self.lazychecks_sql(sql, suffix=suffix)
                self.lazyinfo(sql, noerror=True)
        except (Exception,) as e:  # pragma : no cover
            type_, ex, tb = sys.exc_info()
            self.lazyinfo(sql, exception=e, tb=tb)
            if cpdb():
                pdb.set_trace()
            raise

    diffcommand = "ksdiff"

    #!!!TODO!!!p1 - ./51.hosting/01.fixed.p1.remove_hardcoded_paths
    fnp_difflast = "/Users/jluc/kds2/wk/bin/difflast"

    #!!!TODO!!!p1 - ./51.hosting/01.fixed.p1.remove_hardcoded_paths
    editor = "/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl"

    def lazyinfo(
        self,
        response=None,
        do_inspect=True,
        exception=None,
        tb=None,
        noerror=False,
        check_user_access=True,
        rdbname=None,
        check_rdb_up=True,
    ):
        """
        when called on an exception, try to gather as much as possible and populate
        a shell script you can use to interact with the exception context later

        """

        url = getattr(response, "full_url", "") or getattr(exception, "full_url", "")
        status = getattr(response, "status", "")
        status_code = getattr(response, "status_code", "?")

        if url:
            msg = u"\n%s:url:%s => %s" % (self, url, status_code)
            logger.warning(msg)

        if noerror:
            return

        rdbname = rdbname or tst_constants.TEST_RDBNAME

        echo_message_access = message = scriptname = funcname = linenum = ""

        if check_user_access:

            if isinstance(check_user_access, str):
                username = check_user_access
            else:
                # env.BME_STD_USER will be used.
                username = tst_constants.props.STD_USER

            has_access = check_access_username(rdbname=rdbname, username=username)

            if not has_access:
                message = (
                    "invalid configuration:  User.%s is not allowed for Database.%s"
                    % (username, rdbname)
                )

                echo_message_access = "\necho '!!! %s !!!'" % (message)

                logger.error("%s%s%s" % (logger_header, message, logger_footer))
            else:
                echo_message_access = "\necho User.%s can access Database.%s" % (
                    username,
                    rdbname,
                )

        if check_rdb_up:

            # trying to only check it once per run, as much as possible
            di_access_message = getattr(GenericLazyMixin, "di_access_message", None)
            if di_access_message is None:
                di_access_message = GenericLazyMixin.di_access_message = {}

            db_message = di_access_message.get(rdbname, None)

            if db_message is None:
                mdb = MultiDb(rdbname)
                try:
                    conn = mdb.fast_fail_connect()
                    conn.close()
                    db_message = "\necho connected to Database.%s." % (rdbname)
                except (Exception,) as e:  # pragma : no cover
                    db_message = (
                        "\necho '!!! no connection to Database.%s: exception:%s!!!'"
                        % (rdbname, e)
                    )
                di_access_message[rdbname] = db_message

            echo_message_access += db_message

            if "!" in echo_message_access:
                echo_message_access += """
echo -n "Continue with any key"
read CONT                
"""

        # pdb.set_trace()

        lazy = getattr(self, "lazytemp", None)
        fnp_exp = getattr(lazy, "fnp_exp", None)
        fnp_got = getattr(lazy, "fnp_got", None)

        if do_inspect:
            li = inspect.stack()
            li.reverse()
            fn_test = None

            for ix, tu_f in enumerate(li[:-1]):
                _scriptname = tu_f[1]
                _basename = os.path.basename(tu_f[1])
                funcname = tu_f[3]
                line = tu_f[4][0].rstrip()
                linenum = tu_f[2]

                if "-v" in sys.argv:

                    ppp(
                        dict(
                            _scriptname=_scriptname,
                            funcname=funcname,
                            line=line,
                            linenum=linenum,
                        ),
                        "\ndi_inspect",
                    )

                if _basename.startswith("test_") and funcname.startswith("test_"):
                    scriptname = _scriptname

                    # if rpdb(): # pragma : no cover
                    #     pdb.set_trace()

                    break
            else:
                pass
            editor = self.editor

        if 1:
            logger.info("\n\n%s %s %s\n\n" % (self.diffcommand, fnp_exp, fnp_got))

            vars_ = dict(
                url=url,
                message=message,
                candiff=bool(fnp_exp and fnp_got) * "1",
                linenum=linenum,
                scriptname=scriptname,
                funcname=funcname,
                status=status,
                status_code=status_code,
                fnp_got=fnp_got,
                fnp_exp=fnp_exp,
                editor=self.editor,
                echo_message_access=echo_message_access,
            )

            with open(self.fnp_difflast, "w") as fo:
                fo.write(fill_template(tmpl_difflast, vars_))


#######################################################
# The template below is used to write a `difflast.sh` script on each
# failing test, via `lazyinfo()`.  the intent is to get
# a sample of quick commands:
#   `difflast`       - displays the difference using your diff utility
#   `difflast -cp`   - copies the got/received file to the exp file.
#   `difflast -url`  - if there's a url associated, will launch your browser at
#   `difflast -edit` - tries to open the text editor at the reported error line.
#   etc...
#######################################################


tmpl_difflast = """#!/usr/bin/env bash

url="%(url)s"
scriptname=%(scriptname)s
linenum=%(linenum)s
funcname=%(funcname)s
editor='%(editor)s'
candiff=%(candiff)s
fnp_got="%(fnp_got)s"
fnp_exp="%(fnp_exp)s"
message="%(message)s"

%(echo_message_access)s

#echo "difflast.0:\$url:$url:"

if [ ! -z "$message" ]; then
    echo '********************************'
    echo '* '"$message"' *'
    echo '********************************'
fi


if [ ! -z "$url" ]; then
    echo "url: $url"
    echo status: %(status)s
    echo status_code: %(status_code)s
fi

if [ ! -z "$scriptname" ]; then
    echo "$scriptname $funcname @ line $linenum"
fi

#echo "difflast.1"

if [[ "$@" == "-h" ]]
then

    if [ ! -z "$url" ]; then
        echo "url: $url"
        echo status: %(status)s
        echo status_code: %(status_code)s
    fi



    echo "difflast -cp to copy got to exp which resets expectations"

    if [ ! -z "$candiff" ]; then
        echo "difflast -diff to use diff"
    fi

    echo "difflast -exp to open fnp_exp" 
    echo "difflast -got to open fnp_got" 
    echo "difflast -rmgot to rm fnp_got" 
    echo "difflast -path to show paths" 

    if [ ! -z "$scriptname" ]; then
        echo "difflast -edit to open $scriptname at line $linenum with $editor" 
    fi


    if [ ! -z "$url" ]; then
        echo "difflast -url to open the url" 
    fi

    exit
fi

#echo "difflast.2"


if [ ! -z "$scriptname" ]; then
    if [[ "$1" == "-edit" ]]; then
        "$editor" $scriptname:$linenum
        exit
    fi
fi

#echo "difflast.3"

if [ ! -z "$url" ]; then
    if [[ "$1" == "-url" ]]; then
        open "$url"
        exit
    fi
fi

#echo "difflast.4"

if [ ! -z "$candiff" ]; then

    if [[ "$1" == "-diff" ]]; then
            diff %(fnp_exp)s %(fnp_got)s
            exit
    fi

fi

#echo "difflast.5"


if [[ "$1" == "-path" ]]; then
        echo '%(fnp_exp)s'
        echo '%(fnp_got)s'
        exit
fi

#echo "difflast.6"


if [[ "$1" == "-exp" ]]; then
        "$editor" %(fnp_exp)s
        exit
fi

#echo "difflast.7"


if [[ "$1" == "-rmgot" ]]; then
        rm %(fnp_got)s
        exit
fi

#echo "difflast.8"


if [[ "$1" == "-got" ]]; then
        "$editor"  %(fnp_got)s
        exit
fi

#echo "difflast.9"
if [[ "$1" == "-cp" ]]; then
    echo "this would copy"
    echo "cp "
    echo "%(fnp_got)s"
    echo " to"
    echo "%(fnp_exp)s "

    read -p "Are you sure? " -n 1 -r
    echo    # (optional) move to a new line
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        cp %(fnp_got)s %(fnp_exp)s
    else
        ksdiff %(fnp_exp)s %(fnp_got)s
    fi


else
    ksdiff %(fnp_exp)s %(fnp_got)s
fi

#echo "difflast.10"


"""
