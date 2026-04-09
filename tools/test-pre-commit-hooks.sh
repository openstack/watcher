#!/usr/bin/env bash
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
#
# Verify each pre-commit hook catches its target violation.
# Each test creates a bad file, runs the hook, expects exit code 1 (fail = hook works).
# Must be run from the root of the watcher git repository.

set -uo pipefail

PASS=0; FAIL=0

# Temporary files created inside the repo (required for hooks that match
# repo-relative paths via files:/exclude: patterns).
REPO_TMP=$(mktemp -d -p .)
trap "rm -rf $REPO_TMP" EXIT

# Temporary files that can live outside the repo.
EXT_TMP=$(mktemp -d)
trap "rm -rf $EXT_TMP" EXIT

check() {
    local hook=$1 file=$2 desc=$3
    pre-commit run "$hook" --files "$file" >/dev/null 2>&1 && caught=0 || caught=1
    if [ $caught -eq 1 ]; then
        printf "OK   %-40s %s\n" "$hook" "$desc"
        PASS=$((PASS+1))
    else
        printf "MISS %-40s %s\n" "$hook" "$desc"
        FAIL=$((FAIL+1))
    fi
}

# check_modifies: hook "works" if it modifies the file (fixer hooks that exit 0).
check_modifies() {
    local hook=$1 file=$2 desc=$3
    before=$(md5sum "$file")
    pre-commit run "$hook" --files "$file" >/dev/null 2>&1 || true
    after=$(md5sum "$file")
    if [ "$before" != "$after" ]; then
        printf "OK   %-40s %s\n" "$hook" "$desc"
        PASS=$((PASS+1))
    else
        printf "MISS %-40s %s\n" "$hook" "$desc"
        FAIL=$((FAIL+1))
    fi
}

echo "Testing pre-commit hooks..."
echo ""

# trailing-whitespace — fixer: modifies file and exits 1
printf "hello   \nworld\n" > $EXT_TMP/trail.txt
check trailing-whitespace $EXT_TMP/trail.txt "trailing spaces"

# mixed-line-ending — fixer: modifies and exits 1
printf "line1\r\nline2\n" > $EXT_TMP/mixed.txt
check mixed-line-ending $EXT_TMP/mixed.txt "CRLF in LF file"

# fix-byte-order-marker — fixer: modifies and exits 1
printf '\xef\xbb\xbfhello' > $EXT_TMP/bom.txt
check fix-byte-order-marker $EXT_TMP/bom.txt "UTF-8 BOM"

# check-executables-have-shebangs — needs types: [text, executable]
printf "just a script\n" > $EXT_TMP/noShebang.sh
chmod +x $EXT_TMP/noShebang.sh
check check-executables-have-shebangs $EXT_TMP/noShebang.sh "executable without shebang"

# check-shebang-scripts-are-executable
printf "#!/bin/bash\necho hi\n" > $EXT_TMP/notExec.sh
chmod -x $EXT_TMP/notExec.sh
check check-shebang-scripts-are-executable $EXT_TMP/notExec.sh "shebang without executable bit"

# check-yaml
printf "key: [\nbad yaml\n" > $EXT_TMP/bad.yaml
check check-yaml $EXT_TMP/bad.yaml "invalid YAML"

# check-json
printf '{"key": bad}' > $EXT_TMP/bad.json
check check-json $EXT_TMP/bad.json "invalid JSON"

# check-ast
printf "def foo(\n" > $EXT_TMP/syntax.py
check check-ast $EXT_TMP/syntax.py "Python syntax error"

# check-added-large-files (>8MB default)
dd if=/dev/zero bs=1M count=9 2>/dev/null > $EXT_TMP/large.bin
check check-added-large-files $EXT_TMP/large.bin "file >8MB"

# detect-private-key — split the marker so this file itself is not flagged
MARKER="-----BEGIN RSA PRIVATE ""KEY-----"
printf -- "%s\nMIIEowIBAAK\n-----END RSA PRIVATE KEY-----\n" "$MARKER" > $EXT_TMP/key.txt
check detect-private-key $EXT_TMP/key.txt "private key pattern"

# check-merge-conflict — hook skips unless inside an active git merge, so we run
# the hook script directly with --assume-in-merge to force the check.
printf "<<<<<<< HEAD\nfoo\n=======\nbar\n>>>>>>> branch\n" > $REPO_TMP/conflict.txt
pre-commit run check-merge-conflict --files $REPO_TMP/conflict.txt \
    --hook-stage manual >/dev/null 2>&1 || true
# Run script directly via its entry point with --assume-in-merge
venv=$(find ~/.cache/pre-commit -path "*/py_env*/bin/check-merge-conflict" 2>/dev/null | head -1)
if [ -n "$venv" ]; then
    "$venv" --assume-in-merge $REPO_TMP/conflict.txt >/dev/null 2>&1 && caught=0 || caught=1
    if [ $caught -eq 1 ]; then
        printf "OK   %-40s %s\n" "check-merge-conflict" "conflict markers (--assume-in-merge)"
        PASS=$((PASS+1))
    else
        printf "MISS %-40s %s\n" "check-merge-conflict" "conflict markers (--assume-in-merge)"
        FAIL=$((FAIL+1))
    fi
else
    printf "SKIP %-40s %s\n" "check-merge-conflict" "entry point not found in pre-commit cache"
fi

# debug-statements
printf "import pdb\npdb.set_trace()\n" > $EXT_TMP/debug.py
check debug-statements $EXT_TMP/debug.py "pdb.set_trace()"

# check-docstring-first
printf 'x = 1\n"""docstring after code."""\n' > $EXT_TMP/docfirst.py
check check-docstring-first $EXT_TMP/docfirst.py "code before docstring"

# ruff-check — use F821 (undefined name) which cannot be auto-fixed
printf "print(undefined_var)\n" > $EXT_TMP/ruff.py
check ruff-check $EXT_TMP/ruff.py "undefined name (F821, not auto-fixable)"

# ruff-format — fixer: reformats the file (exits 0 but modifies the content)
printf "x=1+2\n" > $REPO_TMP/fmt.py
check_modifies ruff-format $REPO_TMP/fmt.py "unformatted code (file modified)"

# hacking — bare except (H201)
printf "try:\n    pass\nexcept:\n    pass\n" > $EXT_TMP/hack.py
check hacking $EXT_TMP/hack.py "bare except (H201)"

# bandit — hardcoded password (B105)
printf "password = 'hunter2'\n" > $EXT_TMP/bandit.py
check bandit $EXT_TMP/bandit.py "hardcoded password (B105)"

# codespell — common misspelling written via variable to avoid self-triggering
MISSPELLING="te""h"  # codespell:ignore te
printf "This is %s codespell test\n" "$MISSPELLING" > $EXT_TMP/spell.txt
check codespell $EXT_TMP/spell.txt "misspelling"  # codespell:ignore teh

# sphinx-lint — files: ^doc/ requires a repo-relative path under doc/
printf "See \`something\`.\n" > $REPO_TMP/bad.rst
# sphinx-lint files: filter is ^doc/|^releasenotes/|^api-guide/
# so create it under doc/ to match
mkdir -p doc
printf "See \`something\`.\n" > doc/_test_sphinxlint_tmp.rst
check sphinx-lint doc/_test_sphinxlint_tmp.rst "default role (no double backticks)"
rm -f doc/_test_sphinxlint_tmp.rst

# doc8 — files: \.rst$ requires the file to be inside the repo.
# Use prose (with spaces) — doc8 exempts RST adornments (repeated single chars).
printf "This line is intentionally far too long for doc8 and should trigger a D001 line length violation in the checker\n" > $REPO_TMP/long.rst
check doc8 $REPO_TMP/long.rst "line >79 chars in rst (D001)"

# check-case-conflict: hard to trigger on a case-sensitive FS
printf "SKIP %-40s %s\n" "check-case-conflict" "requires case-insensitive FS"

echo ""
echo "Results: $PASS OK, $FAIL missed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
