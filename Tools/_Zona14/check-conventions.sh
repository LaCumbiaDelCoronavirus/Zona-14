#!/usr/bin/env bash
# check-conventions.sh — Zona-14 convention validator.
# See CONTRIBUTING.md §10 and Tools/_Zona14/README.md for detail.
#
# Usage: check-conventions.sh <base-ref> <head-ref>
# Exit 0 on pass (with or without warnings), 1 on any fatal failure, 2 on usage error.

set -u

FAIL=0
WARN=0
CACHED=0

if [[ $# -eq 1 && "$1" == "--cached" ]]; then
    CACHED=1
    BASE="HEAD"
    HEAD="HEAD"
elif [[ $# -eq 2 ]]; then
    BASE="$1"
    HEAD="$2"
else
    echo "Usage: $0 <base-ref> <head-ref>" >&2
    echo "       $0 --cached" >&2
    exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: 'jq' is required. Install with: sudo apt install jq  (or: brew install jq)" >&2
    exit 2
fi

if [[ "$CACHED" == 1 ]]; then
    COMMIT_MSGS=""
    CHANGED_FILES="$(git diff --name-status --cached 2>/dev/null || true)"
else
    COMMIT_MSGS="$(git log --format=%B "$BASE..$HEAD" 2>/dev/null || echo "")"
    CHANGED_FILES="$(git diff --name-status "$BASE..$HEAD" 2>/dev/null || true)"
fi

# Normalise renames before anything reads CHANGED_FILES.
#
# git reports a rename as a three-field row "R<score>\told\tnew". Every check below
# filters on a two-field "status\tpath" shape, and all but one accept only A/M (or D),
# so an unnormalised R row is silently dropped - a renamed file could be edited without
# a marker and sail through the §3 gate. Expand each rename into the two events it
# actually is: the new path was added/modified, the old path was deleted.
normalise_renames() {
    local status path newpath
    while IFS=$'\t' read -r status path newpath; do
        [[ -z "${status:-}" ]] && continue
        if [[ "$status" == R* && -n "${newpath:-}" ]]; then
            printf 'M\t%s\n' "$newpath"
            printf 'D\t%s\n' "$path"
        else
            printf '%s\t%s\n' "$status" "$path"
        fi
    done
}
CHANGED_FILES="$(normalise_renames <<<"$CHANGED_FILES")"

PR_TITLE="${PR_TITLE:-}"

is_upstream_port() {
    grep -qF '[upstream-port]' <<<"$COMMIT_MSGS$PR_TITLE"
}

is_custom_license() {
    grep -qF '[custom-license]' <<<"$PR_TITLE$COMMIT_MSGS"
}

fail() {
    echo "FAIL: $*" >&2
    FAIL=1
}

warn() {
    echo "WARN: $*" >&2
    WARN=1
}

# ============================================================
# Check 1: Namespace-folder alignment for files under _Zona14/
# ============================================================
check_namespace_alignment() {
    while IFS=$'\t' read -r status path newpath; do
        [[ -z "${status:-}" ]] && continue
        [[ "$status" == A || "$status" == M ]] || continue
        [[ "$path" == *.cs ]] || continue
        [[ "$path" == *"/_Zona14/"* ]] || continue
        [[ -f "$path" ]] || continue

        case "$path" in
            Content.Server/_Zona14/*)                     expected="Content.Server._Zona14" ;;
            Content.Client/_Zona14/*)                     expected="Content.Client._Zona14" ;;
            Content.Shared/_Zona14/*)                     expected="Content.Shared._Zona14" ;;
            Content.IntegrationTests/Tests/_Zona14/*)     expected="Content.IntegrationTests.Tests._Zona14" ;;
            *)                                             continue ;;
        esac

        ns_line=$(grep -m1 -E '^namespace ' "$path" 2>/dev/null || true)
        if [[ -z "$ns_line" ]]; then
            fail "$path: no 'namespace' declaration found (files under _Zona14/ must declare a namespace starting with $expected)"
            continue
        fi

        escaped=$(printf '%s' "$expected" | sed 's/\./\\./g')
        if ! grep -qE "^namespace ${escaped}(\\.|;| *$)" <<<"$ns_line"; then
            actual=$(sed -E 's/^namespace +//; s/[;{]?$//; s/ +$//' <<<"$ns_line")
            fail "$path: namespace should start with '$expected' but is '$actual'"
        fi
    done <<<"$CHANGED_FILES"
}

# ============================================================
# Check 2: Upstream-edit marker (skipped if [upstream-port])
# ============================================================
check_upstream_edit_marker() {
    is_upstream_port && return 0

    while IFS=$'\t' read -r status path newpath; do
        [[ -z "${status:-}" ]] && continue
        [[ "$status" == A || "$status" == M ]] || continue
        [[ "$path" == *"/_Zona14/"* ]] && continue

        case "$path" in
            Content.Server/*|Content.Client/*|Content.Shared/*|Content.IntegrationTests/*|Resources/Prototypes/*|Resources/Locale/*) ;;
            *) continue ;;
        esac

        case "$path" in
            *.cs|*.xaml|*.xaml.cs) marker='// Zona14' ;;
            *.yml|*.yaml|*.ftl)    marker='# Zona14' ;;
            *)                      continue ;;
        esac

        if [[ "$CACHED" == 1 ]]; then
            added=$(git diff --cached -- "$path" 2>/dev/null \
                        | grep -E '^\+[^+]' \
                        | sed 's/^.//' \
                        | grep -v '^[[:space:]]*$' \
                        || true)
        else
            added=$(git diff "$BASE..$HEAD" -- "$path" 2>/dev/null \
                        | grep -E '^\+[^+]' \
                        | sed 's/^.//' \
                        | grep -v '^[[:space:]]*$' \
                        || true)
        fi
        [[ -z "$added" ]] && continue

        if ! grep -qF "$marker" <<<"$added"; then
            fail "$path: added lines outside _Zona14/ without a '$marker' marker (see CONTRIBUTING.md §3; tag PR with [upstream-port] for pure merges)"
        fi
    done <<<"$CHANGED_FILES"
}

# ============================================================
# Check 3: Misfiled namespace
# ============================================================
check_misfiled_namespace() {
    while IFS=$'\t' read -r status path newpath; do
        [[ -z "${status:-}" ]] && continue
        [[ "$status" == A || "$status" == M ]] || continue
        [[ "$path" == *.cs ]] || continue
        [[ "$path" == *"/_Zona14/"* ]] && continue
        [[ -f "$path" ]] || continue

        if grep -qE '^namespace [A-Za-z0-9.]*\._Zona14(\.|;| *$)' "$path" 2>/dev/null; then
            fail "$path: outside _Zona14/ but declares a _Zona14 namespace (move the file under _Zona14/ or fix the namespace)"
        fi
    done <<<"$CHANGED_FILES"
}

# ============================================================
# Check 4: Greenfield outside _Zona14/ (warn only; skipped if [upstream-port])
# ============================================================
check_greenfield() {
    is_upstream_port && return 0

    while IFS=$'\t' read -r status path newpath; do
        [[ -z "${status:-}" ]] && continue
        [[ "$status" == A ]] || continue
        [[ "$path" == *"/_Zona14/"* ]] && continue

        case "$path" in
            Corvax/*|RobustToolbox/*|Pow3r/*) continue ;;
        esac

        case "$path" in
            Content.Server/*.cs|Content.Client/*.cs|Content.Shared/*.cs|Content.IntegrationTests/*.cs) ;;
            Resources/Prototypes/*.yml|Resources/Prototypes/*.yaml) ;;
            *) continue ;;
        esac

        warn "$path: newly added outside _Zona14/ — consider moving under a _Zona14/ folder (reviewer discretion)"
    done <<<"$CHANGED_FILES"
}

# ============================================================
# Check 5: Key-file delete guard
# ============================================================
check_key_file_delete() {
    while IFS=$'\t' read -r status path newpath; do
        [[ "$status" == D ]] || continue
        case "$path" in
            README.md|README.ru.md|LICENSE.TXT|CONTRIBUTING.md|.github/PULL_REQUEST_TEMPLATE.md)
                fail "$path: protected key file deleted"
                ;;
        esac
    done <<<"$CHANGED_FILES"
}

# ============================================================
# Check 6: Asset meta.json license/copyright
# ============================================================
ALLOWED_LICENSES_RE='^(CC-BY-SA-3\.0|CC-BY-SA-4\.0|CC-BY-4\.0|CC0-1\.0|OFL-1\.1|Apache-2\.0|MIT)$'

check_meta_json_license() {
    while IFS=$'\t' read -r status path newpath; do
        [[ -z "${status:-}" ]] && continue
        [[ "$status" == A || "$status" == M ]] || continue
        [[ "$path" == Resources/* ]] || continue
        [[ "$(basename "$path")" == "meta.json" ]] || continue
        [[ -f "$path" ]] || continue

        if ! jq empty "$path" 2>/dev/null; then
            fail "$path: invalid JSON"
            continue
        fi

        license=$(jq -r '.license // ""' "$path")
        copyright=$(jq -r '.copyright // ""' "$path")

        if [[ -z "$license" ]]; then
            fail "$path: missing or empty 'license' (SPDX identifier required; SS14 default is \"CC-BY-SA-3.0\")"
        elif ! is_custom_license && ! [[ "$license" =~ $ALLOWED_LICENSES_RE ]]; then
            fail "$path: 'license' value '$license' is not on the Zona-14 allowlist — add '[custom-license]' to the PR title to override (CONTRIBUTING.md §6)"
        fi

        if [[ -z "$copyright" ]]; then
            fail "$path: missing or empty 'copyright' (human-readable attribution required)"
        fi

        if [[ "$status" == M ]]; then
            base_license=$(git show "$BASE:$path" 2>/dev/null | jq -r '.license // ""' 2>/dev/null || true)
            if [[ -n "$base_license" && -z "$license" ]]; then
                fail "$path: 'license' field was present on base ('$base_license') but removed in this PR (license regression — never drop license fields)"
            fi
            base_copyright=$(git show "$BASE:$path" 2>/dev/null | jq -r '.copyright // ""' 2>/dev/null || true)
            if [[ -n "$base_copyright" && -z "$copyright" ]]; then
                fail "$path: 'copyright' field was present on base but removed in this PR (attribution regression — augment, don't remove)"
            fi
        fi
    done <<<"$CHANGED_FILES"
}

# ============================================================
# Check 7: No global subscribers to action-attempt events outside Content.Shared/
# ============================================================
# Component-targeted subscribers (SubscribeLocalEvent<MyComponent, EventX>) are fine;
# only global no-component subscribers break prediction symmetry — they cancel on
# one side without the matching cancel on the other, producing mispredict snap-backs.
check_no_global_attempt_subscribers() {
    local offenders
    offenders=$(grep -rEn \
        'SubscribeLocalEvent<[[:space:]]*(ShotAttemptedEvent|AttackAttemptEvent|BeforeThrowEvent)[[:space:]]*>' \
        Content.Server Content.Client 2>/dev/null || true)

    if [[ -n "$offenders" ]]; then
        while IFS= read -r line; do
            fail "$line: global subscriber to an action-attempt event in Content.Server/ or Content.Client/ breaks prediction symmetry — move to Content.Shared/, or use SubscribeLocalEvent<TComp, TEvent>"
        done <<<"$offenders"
    fi
}

# ============================================================
# Check 8: YAML data-prototype `categories`/`suffix` guard
# ============================================================
check_yaml_data_prototypes() {
    local yaml_files=()
    while IFS=$'\t' read -r status path newpath; do
        [[ -z "${status:-}" ]] && continue
        [[ "$status" == A || "$status" == M || "$status" == R* ]] || continue
        [[ "$path" == *.yml || "$path" == *.yaml ]] || continue
        yaml_files+=("$path")
    done <<<"$CHANGED_FILES"

    if [[ ${#yaml_files[@]} -eq 0 ]]; then
        return 0
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        warn "python3 not available; skipping YAML data-prototype check"
        return 0
    fi

    local script
    script="$(dirname "$0")/check-yaml-data-prototypes.py"
    if [[ ! -f "$script" ]]; then
        warn "check-yaml-data-prototypes.py not found; skipping YAML data-prototype check"
        return 0
    fi

    if ! python3 "$script" "${yaml_files[@]}"; then
        FAIL=1
    fi
}

# ============================================================
# Run
# ============================================================

if [[ "$CACHED" == 1 ]]; then
    echo "=== Zona-14 convention check: staged changes ==="
else
    echo "=== Zona-14 convention check: $BASE..$HEAD ==="
fi
is_upstream_port && echo "(PR is tagged [upstream-port]; checks 2 and 4 are skipped)"
is_custom_license && echo "(PR is tagged [custom-license]; check 6 allows non-allowlist SPDX values)"
echo

check_namespace_alignment
check_upstream_edit_marker
check_misfiled_namespace
check_greenfield
check_key_file_delete
check_meta_json_license
check_no_global_attempt_subscribers
check_yaml_data_prototypes

echo
if [[ $FAIL -eq 0 ]]; then
    if [[ $WARN -gt 0 ]]; then
        echo "=== PASSED with warnings. ==="
    else
        echo "=== PASSED. ==="
    fi
    exit 0
else
    echo "=== FAILED. See CONTRIBUTING.md for the rules. ==="
    exit 1
fi
