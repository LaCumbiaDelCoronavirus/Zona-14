# `Tools/_Zona14`

Scripts that enforce the Zona-14 coding conventions documented in the root-level [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## `check-conventions.sh`

PR-diff validator. Runs the checks described in `CONTRIBUTING.md §10`:

1. Namespace–folder alignment (fatal)
2. Upstream-edit `// Zona14:` / `# Zona14:` marker enforcement (fatal; skipped on `[upstream-port]` PRs)
3. Misfiled `_Zona14` namespace guard (fatal)
4. Greenfield-outside-`_Zona14/` warning (non-fatal; skipped on `[upstream-port]` PRs)
5. Key-file delete guard (fatal)
6. Asset `meta.json` `license` / `copyright` enforcement (fatal; allowlist override via `[custom-license]`)
7. No global subscribers to action-attempt events (fatal)
8. YAML data-prototype `categories`/`suffix` guard (fatal)

### Usage

```bash
bash Tools/_Zona14/check-conventions.sh <base-ref> <head-ref>
```

Typical local invocation (before pushing):

```bash
bash Tools/_Zona14/check-conventions.sh origin/master HEAD
```

The pre-commit hook uses the `--cached` form:

```bash
bash Tools/_Zona14/check-conventions.sh --cached
```

The workflow [`.github/workflows/zona14-convention.yml`](../../.github/workflows/zona14-convention.yml) runs the same script on every PR against `master`.

### Environment variables

- `PR_TITLE` — optional. Set by the CI workflow from `github.event.pull_request.title`. Used to detect `[upstream-port]` and `[custom-license]` tags. When unset, only commit messages in `base..head` are inspected for tags.

### Dependencies

- `git`, `grep`, `sed`, `awk` — standard on any Linux/macOS shell.
- `jq` — for parsing `meta.json`. Install with `sudo apt install jq` or `brew install jq`.
- `python3` and `pyyaml` — for the YAML data-prototype guard. Install with `python3 -m pip install -r Tools/_Zona14/requirements.txt`.

### Exit codes

- `0` — pass (possibly with warnings on stderr).
- `1` — at least one fatal check failed.
- `2` — usage error or missing dependency (`jq`).

## `test-check-conventions.sh`

Regression tests for `check-conventions.sh`. Run them after touching that script:

```bash
bash Tools/_Zona14/test-check-conventions.sh
```

Case 3 is the one with history behind it. `git` reports a rename as a three-field
`R<score>\told\tnew` row, while every check reads a two-field `status\tpath` shape and
accepts only `A`/`M` (or `D`). An unnormalised `R` row was therefore dropped by all but
one check, so renaming a file outside `_Zona14/` and editing it in the same commit slipped
past the §3 marker gate with a green run. `normalise_renames()` now expands each rename
into the two events it really is (`M` on the new path, `D` on the old) before any check
reads the list.

## `check-z14-consistency.py`

Whole-tree consistency checks. `check-conventions.sh` validates the **diff**; this
validates the **resulting prototype tree** — the class of defect a green diff cannot rule
out, because each file is individually valid and only the combination is wrong. Every
check corresponds to a bug that actually shipped:

| Check | Catches |
| --- | --- |
| `recipe-ambiguity` | Two craft recipes with identical ingredients and different results. Selection is first-match-and-return over an arbitrarily ordered enumeration, so which one the player gets is a coin flip. |
| `dead-ingredient` | A `Z14` ingredient nothing produces. Matching is by exact prototype id with no parent tolerance, so the recipe silently never fires. |
| `armour-override` | An entity under a `Z14ArmorBaseT*` tier base that re-declares `Armor.modifiers` or `GrantsArtifactSlots`. Both are single DataFields with no push-inheritance, so the child replaces the tier wholesale. |
| `locale-drift` | A `_Zona14` entity with no locale key, or a `.desc` whose stated round count contradicts the real `capacity`. FTL wins over YAML, so the YAML text players never see can drift freely. |
| `locale-truncation` | Locale names cut off mid-token (unbalanced `"`, `«»`, `“”`) — a past translation pass mangled every name containing a quotation mark. |
| `clone-drift` | A reference inside `_Zona14/` naming an upstream id that has a `Z14` twin. The twin exists so a rebalance survives the next upstream merge; a missed reference means that rebalance silently does nothing. |

**Crafting ingredients are deliberately exempt from `clone-drift`.** Every loot table grants
the *upstream* material id, and matching is by exact id, so repointing an ingredient to its
`Z14` twin makes the recipe unmatchable. The twins share a `stackType`, so the two merge in
a player's inventory and the breakage stays invisible until someone reports that a recipe
refuses looted material. Recipe *results* are checked; ingredients are not.

### Usage

```bash
python3 Tools/_Zona14/check-z14-consistency.py
```

Pre-existing debt lives in `z14-consistency-baseline.json`, so the script exits non-zero
only for findings the baseline does not already record. After a deliberate, reviewed
deferral, re-record it:

```bash
python3 Tools/_Zona14/check-z14-consistency.py --update-baseline
```

Do not run `--update-baseline` to silence a finding you have not looked at — the baseline
is a record of accepted debt, and the diff on it is what a reviewer reads. `--check NAME`
runs a single check; `--verbose` lists findings that are already baselined.

## `hooks/pre-commit`

Git pre-commit hook that runs `check-conventions.sh` automatically before each commit.

### Install

```bash
git config core.hooksPath Tools/_Zona14/hooks
```

The hook skips gracefully if `jq` is missing (prints a warning instead of blocking the commit).

## `check-yaml-data-prototypes.py`

Python script invoked by `check-conventions.sh` to ensure `categories` and `suffix` are only used on `- type: entity` prototypes. Data prototypes such as `stWarZone`, `stBandShopListings`, `persistentCraftRecipe`, `vendingMachineInventory`, and `shopPreset` do not accept those entity fields and the YAML Linter will reject them.

## `generate-vendor-preset.py`

Generates a `shopPreset` YAML from a CSV or Excel catalog. Expected columns: `id`, `price`, `category`. It validates item IDs against `Resources/Prototypes/_Zona14/` and reports missing IDs.

### Example

```bash
python3 Tools/_Zona14/generate-vendor-preset.py \
  --input vendor.csv \
  --output Resources/Prototypes/_Zona14/ShopPresets/NPCShops/MyVendor.yml \
  --preset-id Z14MyVendorPreset \
  --min-sell-price 1
```

## `update-devin-tools.sh`

Fetches the `devin-tools` branch from origin and copies `AGENTS.md` and `.agents/skills/` into the working tree. Adds those files to `.git/info/exclude` so they are ignored in `master` and not removed by `git clean -fd`.

## `requirements.txt`

Python packages used by the helper scripts (`pyyaml`, `openpyxl`). Install with:

```bash
python3 -m pip install -r Tools/_Zona14/requirements.txt
```
