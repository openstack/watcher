# Copyright (c) 2014 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import re


def flake8ext(f):
    """Decorator to indicate flake8 extension.

    This is borrowed from hacking.core.flake8ext(), but at now it is used
    only for unit tests to know which are watcher flake8 extensions.
    """
    f.name = __name__
    f.version = '0.0.1'
    f.skip_on_py3 = False
    return f


# Guidelines for writing new hacking checks
#
#  - Use only for Watcher specific tests. OpenStack general tests
#    should be submitted to the common 'hacking' module.
#  - Pick numbers in the range N3xx. Find the current test with
#    the highest allocated number and then pick the next value.
#  - Keep the test method code in the source file ordered based
#    on the N3xx value.
#  - List the new rule in the top level HACKING.rst file

_all_log_levels = {
    'reserved': '_',  # this should never be used with a log unless
                      # it is a variable used for a log message and
                      # a exception
    'error': '_LE',
    'info': '_LI',
    'warning': '_LW',
    'critical': '_LC',
    'exception': '_LE',
}
_all_hints = set(_all_log_levels.values())


def _regex_for_level(level, hint):
    return r".*LOG\.%(level)s\(\s*((%(wrong_hints)s)\(|'|\")" % {
        'level': level,
        'wrong_hints': '|'.join(_all_hints - set([hint])),
    }


log_warn = re.compile(
    r"(.)*LOG\.(warn)\(\s*('|\"|_)")
unittest_imports_dot = re.compile(r"\bimport[\s]+unittest\b")
unittest_imports_from = re.compile(r"\bfrom[\s]+unittest\b")
re_redundant_import_alias = re.compile(r".*import (.+) as \1$")


@flake8ext
def use_jsonutils(logical_line, filename):
    msg = "N321: jsonutils.%(fun)s must be used instead of json.%(fun)s"

    # Skip list is currently empty.
    json_check_skipped_patterns = []

    for pattern in json_check_skipped_patterns:
        if pattern in filename:
            return

    if "json." in logical_line:
        json_funcs = ['dumps(', 'dump(', 'loads(', 'load(']
        for f in json_funcs:
            pos = logical_line.find('json.%s' % f)
            if pos != -1:
                yield (pos, msg % {'fun': f[:-1]})


@flake8ext
def no_translate_debug_logs(logical_line, filename):
    """Check for 'LOG.debug(_(' and 'LOG.debug(_Lx('

    As per our translation policy,
    https://wiki.openstack.org/wiki/LoggingStandards#Log_Translation
    we shouldn't translate debug level logs.

    * This check assumes that 'LOG' is a logger.

    N319
    """
    for hint in _all_hints:
        if logical_line.startswith("LOG.debug(%s(" % hint):
            yield (0, "N319 Don't translate debug level logs")


@flake8ext
def check_assert_called_once_with(logical_line, filename):
    # Try to detect unintended calls of nonexistent mock methods like:
    #    assert_called_once
    #    assertCalledOnceWith
    #    assert_has_called
    #    called_once_with
    if 'watcher/tests/' in filename:
        if '.assert_called_once_with(' in logical_line:
            return
        uncased_line = logical_line.lower().replace('_', '')

        check_calls = ['.assertcalledonce', '.calledoncewith']
        if any(x for x in check_calls if x in uncased_line):
            msg = ("N322: Possible use of no-op mock method. "
                   "please use assert_called_once_with.")
            yield (0, msg)

        if '.asserthascalled' in uncased_line:
            msg = ("N322: Possible use of no-op mock method. "
                   "please use assert_has_calls.")
            yield (0, msg)


@flake8ext
def check_python3_xrange(logical_line):
    if re.search(r"\bxrange\s*\(", logical_line):
        yield (0, "N325: Do not use xrange. Use range for large loops.")


@flake8ext
def check_no_basestring(logical_line):
    if re.search(r"\bbasestring\b", logical_line):
        msg = ("N326: basestring is not Python3-compatible, use str instead.")
        yield (0, msg)


@flake8ext
def check_python3_no_iteritems(logical_line):
    if re.search(r".*\.iteritems\(\)", logical_line):
        msg = ("N327: Use dict.items() instead of dict.iteritems().")
        yield (0, msg)


@flake8ext
def check_asserttrue(logical_line, filename):
    if 'watcher/tests/' in filename:
        if re.search(r"assertEqual\(\s*True,[^,]*(,[^,]*)?\)", logical_line):
            msg = ("N328: Use assertTrue(observed) instead of "
                   "assertEqual(True, observed)")
            yield (0, msg)
        if re.search(r"assertEqual\([^,]*,\s*True(,[^,]*)?\)", logical_line):
            msg = ("N328: Use assertTrue(observed) instead of "
                   "assertEqual(True, observed)")
            yield (0, msg)


@flake8ext
def check_assertfalse(logical_line, filename):
    if 'watcher/tests/' in filename:
        if re.search(r"assertEqual\(\s*False,[^,]*(,[^,]*)?\)", logical_line):
            msg = ("N329: Use assertFalse(observed) instead of "
                   "assertEqual(False, observed)")
            yield (0, msg)
        if re.search(r"assertEqual\([^,]*,\s*False(,[^,]*)?\)", logical_line):
            msg = ("N329: Use assertFalse(observed) instead of "
                   "assertEqual(False, observed)")
            yield (0, msg)


@flake8ext
def check_assertempty(logical_line, filename):
    if 'watcher/tests/' in filename:
        msg = ("N330: Use assertEqual(*empty*, observed) instead of "
               "assertEqual(observed, *empty*). *empty* contains "
               "{}, [], (), set(), '', \"\"")
        empties = r"(\[\s*\]|\{\s*\}|\(\s*\)|set\(\s*\)|'\s*'|\"\s*\")"
        reg = r"assertEqual\(([^,]*,\s*)+?%s\)\s*$" % empties
        if re.search(reg, logical_line):
            yield (0, msg)


@flake8ext
def check_assertisinstance(logical_line, filename):
    if 'watcher/tests/' in filename:
        if re.search(r"assertTrue\(\s*isinstance\(\s*[^,]*,\s*[^,]*\)\)",
                     logical_line):
            msg = ("N331: Use assertIsInstance(observed, type) instead "
                   "of assertTrue(isinstance(observed, type))")
            yield (0, msg)


@flake8ext
def check_assertequal_for_httpcode(logical_line, filename):
    msg = ("N332: Use assertEqual(expected_http_code, observed_http_code) "
           "instead of assertEqual(observed_http_code, expected_http_code)")
    if 'watcher/tests/' in filename:
        if re.search(r"assertEqual\(\s*[^,]*,[^,]*HTTP[^\.]*\.code\s*\)",
                     logical_line):
            yield (0, msg)


@flake8ext
def check_log_warn_deprecated(logical_line, filename):
    msg = "N333: Use LOG.warning due to compatibility with py3"
    if log_warn.match(logical_line):
        yield (0, msg)


@flake8ext
def check_oslo_i18n_wrapper(logical_line, filename, noqa):
    """Check for watcher.i18n usage.

    N340(watcher/foo/bar.py): from watcher.i18n import _
    Okay(watcher/foo/bar.py): from watcher.i18n import _  # noqa
    """

    if noqa:
        return

    split_line = logical_line.split()
    modulename = os.path.normpath(filename).split('/')[0]
    bad_i18n_module = '%s.i18n' % modulename

    if (len(split_line) > 1 and split_line[0] in ('import', 'from')):
        if (split_line[1] == bad_i18n_module or
            modulename != 'watcher' and split_line[1] in ('watcher.i18n',
                                                          'watcher._i18n')):
            msg = ("N340: %(found)s is found. Use %(module)s._i18n instead."
                   % {'found': split_line[1], 'module': modulename})
            yield (0, msg)


@flake8ext
def check_builtins_gettext(logical_line, tokens, filename, lines, noqa):
    """Check usage of builtins gettext _().

    N341(watcher/foo.py): _('foo')
    Okay(watcher/i18n.py): _('foo')
    Okay(watcher/_i18n.py): _('foo')
    Okay(watcher/foo.py): _('foo')  # noqa
    """

    if noqa:
        return

    modulename = os.path.normpath(filename).split('/')[0]

    if '%s/tests' % modulename in filename:
        return

    if os.path.basename(filename) in ('i18n.py', '_i18n.py'):
        return

    token_values = [t[1] for t in tokens]
    i18n_wrapper = '%s._i18n' % modulename

    if '_' in token_values:
        i18n_import_line_found = False
        for line in lines:
            split_line = [elm.rstrip(',') for elm in line.split()]
            if (len(split_line) > 1 and split_line[0] == 'from' and
                    split_line[1] == i18n_wrapper and
                    '_' in split_line):
                i18n_import_line_found = True
                break
        if not i18n_import_line_found:
            msg = ("N341: _ from python builtins module is used. "
                   "Use _ from %s instead." % i18n_wrapper)
            yield (0, msg)


@flake8ext
def no_redundant_import_alias(logical_line):
    """Checking no redundant import alias.

    https://bugs.launchpad.net/watcher/+bug/1745527

    N342
    """
    if re.match(re_redundant_import_alias, logical_line):
        yield (0, "N342: No redundant import alias.")


@flake8ext
def import_stock_mock(logical_line):
    """Use python's mock, not the mock library.

    Since we `dropped support for python 2`__, we no longer need to use the
    mock library, which existed to backport py3 functionality into py2.
    Which must be done by saying::

        from unittest import mock

    ...because if you say::

        import mock

    ...you definitely will not be getting the standard library mock. That will
    always import the third party mock library. This check can be removed in
    the future (and we can start saying ``import mock`` again) if we manage to
    purge these transitive dependencies.

    .. __: https://review.opendev.org/#/c/717540

    N366
    """
    if logical_line == 'import mock':
        yield (0, "N366: You must explicitly import python's mock: "
                  "``from unittest import mock``")
