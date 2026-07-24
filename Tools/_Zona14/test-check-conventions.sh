#!/usr/bin/env bash
# Regression tests for check-conventions.sh.
#
# Each case builds a throwaway git repo, stages a change, and asserts the validator's
# exit status. Run from anywhere:  bash Tools/_Zona14/test-check-conventions.sh
#
# Case 3 is the one that matters historically: git reports a rename as a three-field
# "R<score>\told\tnew" row, and every check filters on a two-field "status\tpath" shape
# accepting only A/M. Before normalise_renames() an R row was dropped by all but one
# check, so renaming a file outside _Zona14/ and editing it in the same commit slipped
# past the §3 marker gate with a green run.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="$SCRIPT_DIR/check-conventions.sh"
PASSED=0
FAILED=0

setup_repo() {
    local dir
    dir="$(mktemp -d)"
    mkdir -p "$dir/Resources/Prototypes/_Stalker" "$dir/Resources/Prototypes/_Zona14" "$dir/Tools/_Zona14"
    cp "$CHECKER" "$dir/Tools/_Zona14/"
    [[ -f "$SCRIPT_DIR/check-yaml-data-prototypes.py" ]] &&
        cp "$SCRIPT_DIR/check-yaml-data-prototypes.py" "$dir/Tools/_Zona14/"
    (
        cd "$dir" || exit 1
        git init -q .
        git config user.email t@example.com
        git config user.name t
        # big enough that a one-line edit still scores as a rename
        for i in $(seq 1 60); do
            printf -- "- type: entity\n  id: Filler%s\n  categories: [ Stuff ]\n" "$i"
        done > Resources/Prototypes/_Stalker/old.yml
        git add -A
        git commit -qm init
    )
    printf '%s' "$dir"
}

expect() {
    local name="$1" want="$2" dir="$3"
    local got
    ( cd "$dir" && bash Tools/_Zona14/check-conventions.sh --cached >/dev/null 2>&1 )
    got=$?
    if [[ "$got" == "$want" ]]; then
        echo "  PASS  $name (exit $got)"
        PASSED=$((PASSED + 1))
    else
        echo "  FAIL  $name (expected exit $want, got $got)"
        FAILED=$((FAILED + 1))
    fi
    rm -rf "$dir"
}

echo "=== check-conventions.sh regression tests ==="

# 1. unmarked edit to an existing file outside _Zona14/ -> must fail
d="$(setup_repo)"
printf -- "  description: unmarked\n" >> "$d/Resources/Prototypes/_Stalker/old.yml"
( cd "$d" && git add -A )
expect "unmarked edit outside _Zona14 fails" 1 "$d"

# 2. same edit, but marked -> must pass
d="$(setup_repo)"
printf -- "  description: marked  # Zona14: added\n" >> "$d/Resources/Prototypes/_Stalker/old.yml"
( cd "$d" && git add -A )
expect "marked edit outside _Zona14 passes" 0 "$d"

# 3. RENAME + unmarked edit outside _Zona14/ -> must fail (the R-row regression)
d="$(setup_repo)"
(
    cd "$d" || exit 1
    git mv Resources/Prototypes/_Stalker/old.yml Resources/Prototypes/_Stalker/new.yml
    printf -- "  description: sneaky unmarked edit\n" >> Resources/Prototypes/_Stalker/new.yml
    git add -A
    # sanity: this case is only meaningful if git actually reports a rename
    git diff --name-status --cached | grep -q '^R' ||
        echo "  WARN  case 3 did not produce an R row; rename detection off"
)
expect "renamed + unmarked edit outside _Zona14 fails" 1 "$d"

# 4. rename + edit inside _Zona14/ -> must pass (markers are not required there)
d="$(setup_repo)"
(
    cd "$d" || exit 1
    git mv Resources/Prototypes/_Stalker/old.yml Resources/Prototypes/_Zona14/new.yml
    printf -- "  description: no marker needed here\n" >> Resources/Prototypes/_Zona14/new.yml
    git add -A
)
expect "renamed + edited inside _Zona14 passes" 0 "$d"

echo
echo "passed: $PASSED  failed: $FAILED"
[[ "$FAILED" -eq 0 ]]
