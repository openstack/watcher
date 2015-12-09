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
import testtools


class TestDocFormatting(testtools.TestCase):
    def _check_lines_wrapping(self, tpl, raw):
        code_block = False
        for i, line in enumerate(raw.split("\n"), start=1):
            # NOTE(ndipanov): Allow code block lines to be longer than 79 ch
            if code_block:
                if not line or line.startswith(" "):
                    continue
                else:
                    code_block = False
            if "::" in line:
                code_block = True
            if "http://" in line or "https://" in line:
                continue
            # Allow lines which do not contain any whitespace
            if re.match("\s*[^\s]+$", line):
                continue
            if code_block is False:
                self.assertTrue(
                    len(line) < 80,
                    msg="%s:%d: Line limited to a maximum of 79 characters." %
                        (tpl, i))

    def _check_no_cr(self, tpl, raw):
        cr = '\r'
        matches = re.findall(cr, raw)
        self.assertEqual(
            len(matches), 0,
            "Found %s literal carriage returns in file %s" %
            (len(matches), tpl))

    def _check_trailing_spaces(self, tpl, raw):
        for i, line in enumerate(raw.split("\n"), start=1):
            trailing_spaces = re.findall(" +$", line)
            self.assertEqual(len(trailing_spaces), 0,
                             "Found trailing spaces on line %s of %s" % (
                                 i, tpl))

    def _check_tab(self, tpl, raw):
        tab = '\t'
        matches = re.findall(tab, raw)
        self.assertEqual(
            len(matches), 0,
            "Found %s tab in file %s" %
            (len(matches), tpl))

    def test_template(self):
        doc_path = os.path.join("doc", 'source')
        for root, dirs, files in os.walk(top=doc_path):
            for file in files:
                absolute_path_file = os.path.join(root, file)

                if not os.path.isdir(absolute_path_file):
                    if not absolute_path_file.endswith(".rst"):
                        continue

                    with open(absolute_path_file) as f:
                        data = f.read()

                    self._check_tab(absolute_path_file, data)
                    self._check_lines_wrapping(absolute_path_file, data)
                    self._check_no_cr(absolute_path_file, data)
                    self._check_trailing_spaces(absolute_path_file, data)
