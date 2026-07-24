#!/usr/bin/env python3
"""Whole-tree consistency checks for the Zona-14 fork.

check-conventions.sh validates the *diff* (markers, namespaces, categories). This
script validates the *resulting prototype tree* - the class of defect that a green
diff cannot rule out, because every file is individually valid and only the
combination is wrong. Every check here corresponds to a bug that actually shipped:

  recipe-ambiguity  Two craft recipes with identical ingredients and different
                    results. Selection is first-match-and-return over an
                    arbitrarily ordered prototype enumeration
                    (SharedCraftingSystem.OnCraftAttempt), so which one a player
                    gets is effectively a coin flip. A Z14 recipe must differ from
                    its _Stalker twin in its INPUTS - normally by taking the Z14
                    blueprint - not only in its output.

  dead-ingredient   A recipe ingredient no loot table, butcher drop, shop category
                    or other recipe produces. Ingredient matching is by exact
                    prototype id with no parent tolerance, so an unreachable
                    ingredient silently makes the recipe uncraftable.

  armour-override   An entity under a Z14ArmorBaseT* tier base that re-declares
                    Armor.modifiers or GrantsArtifactSlots. Both are single
                    DataFields with no push-inheritance, so the child's block
                    replaces the tier's wholesale and the ladder stops meaning
                    anything.

  locale-drift      A YAML description that disagrees with the .ftl string players
                    actually see (FTL wins - LocalizationManager.Entity), or a
                    _Zona14 entity with no locale key at all.

  clone-drift       A reference inside _Zona14/ that names an upstream id which has
                    a Z14 twin. Usually harmless today and load-bearing later: the
                    twin exists so a rebalance survives the next upstream merge, and
                    a missed reference means that rebalance silently does nothing.

Pre-existing debt is carried in a baseline file so the check can gate NEW findings
without demanding a full cleanup first. Exit status is 1 only when findings appear
that the baseline does not already record.

Usage:
    python3 Tools/_Zona14/check-z14-consistency.py [--check NAME] [--verbose]
    python3 Tools/_Zona14/check-z14-consistency.py --update-baseline
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

try:
    import yaml
except ImportError:
    sys.exit("ERROR: pyyaml is required. pip install -r Tools/_Zona14/requirements.txt")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROTO = os.path.join(REPO, "Resources", "Prototypes")
LOCALE = os.path.join(REPO, "Resources", "Locale")
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "z14-consistency-baseline.json")

Z14DIR = "_Zona14/"


# ---------------------------------------------------------------- yaml loading
class SS14Loader(yaml.SafeLoader):
    """SS14 prototypes carry engine tags (!type:, !ntype:) SafeLoader rejects."""


def _any_tag(loader, tag_suffix, node):
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node, deep=True)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node, deep=True)
    return loader.construct_scalar(node)


SS14Loader.add_multi_constructor("!", _any_tag)


def load_tree():
    """Return (docs, parse_failures). docs is a list of (relpath, prototype dict)."""
    docs, failures = [], []
    for dirpath, _, files in os.walk(PROTO):
        for fname in files:
            if not fname.endswith((".yml", ".yaml")):
                continue
            path = os.path.join(dirpath, fname)
            rel = os.path.relpath(path, PROTO).replace("\\", "/")
            try:
                with open(path, encoding="utf-8-sig") as fh:
                    parsed = yaml.load(fh, SS14Loader)
            except Exception as exc:  # noqa: BLE001 - report, do not crash
                failures.append((rel, f"{type(exc).__name__}: {exc}"))
                continue
            if not isinstance(parsed, list):
                continue
            for doc in parsed:
                if isinstance(doc, dict) and doc.get("type"):
                    docs.append((rel, doc))
    return docs, failures


def component(doc, name):
    for comp in doc.get("components") or []:
        if isinstance(comp, dict) and comp.get("type") == name:
            return comp
    return None


def parents_of(doc):
    par = doc.get("parent")
    if par is None:
        return []
    return list(par) if isinstance(par, list) else [par]


# ------------------------------------------------------------------- the model
class Tree:
    def __init__(self):
        self.docs, self.failures = load_tree()
        self.entities = {}
        self.recipes = []
        self.light = []
        for rel, doc in self.docs:
            kind = doc.get("type")
            if kind == "entity" and doc.get("id"):
                self.entities[doc["id"]] = (rel, doc)
            elif kind == "craftRecipe":
                self.recipes.append((rel, doc))
            elif kind == "lightCraftingRecipe":
                self.light.append((rel, doc))
        self._anc = {}

    def ancestry(self, eid, _seen=None):
        if eid in self._anc:
            return self._anc[eid]
        seen = set() if _seen is None else _seen
        out = []
        if eid in self.entities:
            for par in parents_of(self.entities[eid][1]):
                if par in seen:
                    continue
                seen.add(par)
                out.append(par)
                out.extend(self.ancestry(par, seen))
        if _seen is None:
            self._anc[eid] = out
        return out


# ---------------------------------------------------------------- the checks
def check_recipe_ambiguity(tree):
    groups = defaultdict(list)
    for rel, doc in tree.recipes:
        items = doc.get("items")
        if not isinstance(items, dict):
            continue
        key = []
        for name in sorted(items):
            val = items[name] if isinstance(items[name], dict) else {}
            key.append((name, val.get("amount"), bool(val.get("catalyzer"))))
        groups[tuple(key)].append((rel, doc))

    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        results = {tuple(d.get("resultProtos") or []) for _, d in members}
        if len(results) < 2:
            continue  # same output = harmless duplicate
        ids = sorted(d.get("id", "?") for _, d in members)
        out.append({
            "key": " + ".join(sorted(k[0] for k in list(groups.keys())[0])) if False else ids[0],
            "detail": f"{' vs '.join(ids)} share ingredients but produce different results",
            "file": members[0][0],
        })
    return out


def _mentioned_outside_recipes(tree):
    """Every id the tree names somewhere other than a recipe's ingredient list.

    Loot reaches players through a long tail of shapes - StorageFill rows, shop
    category maps, loot-spawner string lists, entity tables, starting gear,
    Butcherable drops, SpawnItemsOnUse, map placements - and enumerating them
    individually just yields false alarms whenever one is missed. Inverting the
    question is far more robust: an ingredient that appears NOWHERE except the
    recipe demanding it cannot possibly be obtainable, whatever the mechanism.
    That under-reports (an id mentioned in a dead shop still counts as mentioned)
    but it never cries wolf, which is what makes it safe to gate CI on.
    """
    seen = set()
    for rel, doc in tree.docs:
        clone = dict(doc)
        if clone.get("type") in ("craftRecipe", "lightCraftingRecipe"):
            clone.pop("items", None)
            clone.pop("steps", None)
        clone.pop("id", None)
        seen.update(re.findall(r"[A-Za-z][A-Za-z0-9_]{3,}", repr(clone)))
    return seen


def check_dead_ingredient(tree):
    """Z14 ingredients with no producer.

    Deliberately limited to Z14-prefixed ingredients. Upstream ids reach players
    through machinery this script does not model - sliceable food, vending
    inventories, reagent grinders, hand-placed map entities - so flagging them is
    all false positives. A Z14 clone, by contrast, only ever exists because this
    fork put it somewhere, so "nothing produces it" is a real finding and exactly
    the shape of the fish-fillet and uni-pulp breaks.
    """
    produced = _mentioned_outside_recipes(tree)
    out = []
    for rel, doc in tree.recipes:
        if not rel.startswith(Z14DIR):
            continue
        for name in (doc.get("items") or {}):
            if not name.startswith("Z14"):
                continue
            if name in produced or name not in tree.entities:
                continue
            out.append({
                "key": f"{doc.get('id')}::{name}",
                "detail": f"recipe {doc.get('id')} needs {name}, which nothing produces",
                "file": rel,
            })
    return out


def check_armour_override(tree):
    tiers = {e for e in tree.entities if re.fullmatch(r"Z14ArmorBaseT\d(PvE|PvP)?", e)}
    out = []
    for eid, (rel, doc) in tree.entities.items():
        if eid in tiers:
            continue  # the ladder itself
        anc = tree.ancestry(eid)
        tier = next((a for a in anc if a in tiers), None)
        if not tier:
            continue
        armour = component(doc, "Armor")
        if armour and "modifiers" in armour:
            out.append({
                "key": f"{eid}::modifiers",
                "detail": f"{eid} re-declares Armor.modifiers under {tier}; the tier block is ignored",
                "file": rel,
            })
        slots = component(doc, "GrantsArtifactSlots")
        if slots and "slots" in slots:
            out.append({
                "key": f"{eid}::slots",
                "detail": f"{eid} hard-codes GrantsArtifactSlots under {tier}",
                "file": rel,
            })
    return out


def _index_locale(root):
    index = {}
    if not os.path.isdir(root):
        return index
    for dirpath, _, files in os.walk(root):
        for fname in files:
            if not fname.endswith(".ftl"):
                continue
            path = os.path.join(dirpath, fname)
            cur = None
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    head = re.match(r"^(ent-[A-Za-z0-9_]+)\s*=\s*(.*)$", line)
                    if head:
                        cur = head.group(1)[4:]
                        index.setdefault(cur, {"name": head.group(2).strip() or None,
                                               "desc": None, "file": path})
                        continue
                    if cur:
                        desc = re.match(r"^\s+\.desc\s*=\s*(.*)$", line)
                        if desc and index[cur]["desc"] is None:
                            index[cur]["desc"] = desc.group(1).strip()
                        if not line.strip():
                            cur = None
    return index


# A number the description presents as "how many rounds are in this container",
# in either shipped language. Anything else that looks like a digit is ignored.
COUNT_PHRASE = re.compile(
    r"(\d+)\s*(?:rounds?|pieces?|shells?|cartridges?)"          # "50 rounds", "30 pieces"
    r"|(?:there are|contains)\s*(\d+)"                          # "there are 30 ..."
    r"|[Вв]\s*(?:коробке|ящике|пачке|упаковке)\s*(\d+)"         # "в коробке 50 штук"
    r"|(\d+)\s*(?:штук|патронов)"                               # "50 штук"
)


def _stated_counts(text):
    return [int(g) for m in COUNT_PHRASE.finditer(text) for g in m.groups() if g]


def check_locale_drift(tree):
    en = _index_locale(os.path.join(LOCALE, "en-US", "_Zona14"))
    ru = _index_locale(os.path.join(LOCALE, "ru-RU", "_Zona14"))
    out = []
    for eid, (rel, doc) in sorted(tree.entities.items()):
        if not rel.startswith(Z14DIR) or doc.get("abstract"):
            continue
        cats = doc.get("categories") or []
        if "HideSpawnMenu" in cats and eid not in en:
            continue
        if doc.get("name") is None and doc.get("description") is None:
            continue
        if eid not in en:
            out.append({"key": f"{eid}::no-en", "detail": f"{eid} has no en-US locale key", "file": rel})
        if eid not in ru:
            out.append({"key": f"{eid}::no-ru", "detail": f"{eid} has no ru-RU locale key", "file": rel})
        # a stated round count that contradicts the real capacity
        cap = None
        for anc in [eid] + tree.ancestry(eid):
            comp = component(tree.entities[anc][1], "BallisticAmmoProvider") if anc in tree.entities else None
            if comp and "capacity" in comp:
                cap = comp["capacity"]
                break
        if cap is None:
            continue
        for tag, table in (("en-US", en), ("ru-RU", ru)):
            row = table.get(eid)
            if not row or not row["desc"] or row["desc"].startswith("{"):
                continue
            # Only compare a number the string actually presents as a round count.
            # Descriptions are full of other digits - calibres ("12.7x55"), armour
            # classes ("penetrates class 4"), model names ("SR-2M") - so a bare
            # digit scan reports nothing but noise.
            stated = _stated_counts(row["desc"])
            if stated and cap not in stated:
                out.append({
                    "key": f"{eid}::cap-{tag}",
                    "detail": f"{eid} {tag} .desc says {stated[0]} rounds but capacity is {cap}",
                    "file": rel,
                })
    return out


# Fields where naming the upstream id instead of the existing Z14 twin is drift:
# the twin was cloned precisely so a rebalance survives the next upstream merge,
# and a reference left pointing upstream means that rebalance silently does nothing.
REF_FIELDS = (
    "clothingPrototype",   # ToggleableClothing hood/helmet
    "damageModifierSet",   # mob armour profile
    "blueprint",           # STBlueprint -> the recipe it teaches
    "startingItem",        # ItemSlots (magazine loaded into a gun)
    "prototype",           # SpawnOnDespawn and friends
)

# INGREDIENTS ARE NOT DRIFT - do not "fix" them.
#
# Crafting matches ingredients by exact prototype id with no parent tolerance, and
# every loot table grants the UPSTREAM material id. Repointing an ingredient to its
# Z14 twin therefore makes the recipe silently unmatchable. The twins share a
# stackType so the two merge in a player's inventory, which hides the breakage until
# someone reports that a recipe refuses looted material. Results are a different
# matter: those the fork does control, so they are checked.
INGREDIENT_KEYS = ("ingredients", "items", "steps")


def check_clone_drift(tree):
    out = []
    for rel, doc in tree.docs:
        if not rel.startswith(Z14DIR):
            continue
        did = doc.get("id")

        scannable = {k: v for k, v in doc.items() if k not in INGREDIENT_KEYS}
        blob = repr(scannable)
        for field in REF_FIELDS:
            for value in re.findall(rf"'{field}':\s*'([A-Za-z0-9_]+)'", blob):
                if value.startswith("Z14") or "Z14" + value not in tree.entities:
                    continue
                out.append({
                    "key": f"{did}::{field}::{value}",
                    "detail": f"{did} {field} -> {value}, but Z14{value} exists",
                    "file": rel,
                })

        # persistentCraftRecipe results (never its ingredients - see above)
        if doc.get("type") == "persistentCraftRecipe":
            for res in doc.get("results") or []:
                value = res.get("proto") if isinstance(res, dict) else None
                if not value or value.startswith("Z14") or "Z14" + value not in tree.entities:
                    continue
                out.append({
                    "key": f"{did}::result::{value}",
                    "detail": f"{did} produces upstream {value}, but Z14{value} exists",
                    "file": rel,
                })
    return out


def check_locale_truncation(tree):
    """Locale strings cut off mid-token.

    A past translation pass mangled names containing quotation marks, leaving
    values like 'Вепрь-12 "Молото' - the closing quote and a letter gone. These
    render as-is to players and are invisible to every other check, so a simple
    balance test on the quote characters the names actually use is worth having.
    """
    out = []
    for lang in ("en-US", "ru-RU"):
        root = os.path.join(LOCALE, lang, "_Zona14")
        for eid, row in sorted(_index_locale(root).items()):
            name = row.get("name")
            if not name:
                continue
            for opener, closer in (('"', '"'), ("«", "»"), ("“", "”")):
                if opener == closer:
                    if name.count(opener) % 2:
                        out.append({
                            "key": f"{eid}::{lang}::quote",
                            "detail": f"{eid} {lang} name has an unbalanced {opener}: {name!r}",
                            "file": os.path.relpath(row["file"], REPO).replace("\\", "/"),
                        })
                elif name.count(opener) != name.count(closer):
                    out.append({
                        "key": f"{eid}::{lang}::quote",
                        "detail": f"{eid} {lang} name has unbalanced {opener}{closer}: {name!r}",
                        "file": os.path.relpath(row["file"], REPO).replace("\\", "/"),
                    })
    return out


CHECKS = {
    "recipe-ambiguity": check_recipe_ambiguity,
    "locale-truncation": check_locale_truncation,
    "dead-ingredient": check_dead_ingredient,
    "armour-override": check_armour_override,
    "locale-drift": check_locale_drift,
    "clone-drift": check_clone_drift,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="append", choices=sorted(CHECKS),
                    help="run only this check (repeatable)")
    ap.add_argument("--update-baseline", action="store_true",
                    help="record current findings as accepted debt and exit 0")
    ap.add_argument("--verbose", action="store_true", help="list every finding")
    args = ap.parse_args()

    tree = Tree()
    if tree.failures:
        print(f"!! {len(tree.failures)} file(s) failed to parse:")
        for rel, err in tree.failures[:10]:
            print(f"   {rel}: {err[:110]}")

    selected = args.check or sorted(CHECKS)
    results = {name: CHECKS[name](tree) for name in selected}

    if args.update_baseline:
        baseline = {n: sorted({f["key"] for f in r}) for n, r in results.items()}
        with open(BASELINE, "w", encoding="utf-8") as fh:
            json.dump(baseline, fh, indent=1, sort_keys=True)
            fh.write("\n")
        total = sum(len(v) for v in baseline.values())
        print(f"baseline written: {total} accepted finding(s) -> {os.path.relpath(BASELINE, REPO)}")
        return 0

    baseline = {}
    if os.path.exists(BASELINE):
        with open(BASELINE, encoding="utf-8") as fh:
            baseline = json.load(fh)

    new_total = 0
    print("\n=== Zona-14 prototype consistency ===")
    for name in selected:
        found = results[name]
        known = set(baseline.get(name, []))
        fresh = [f for f in found if f["key"] not in known]
        new_total += len(fresh)
        status = "OK " if not fresh else "NEW"
        print(f"[{status}] {name:18s} {len(found):5d} finding(s), {len(fresh)} new")
        show = fresh if fresh else (found if args.verbose else [])
        for finding in show[:40]:
            print(f"        {finding['detail']}")
            print(f"          {finding['file']}")
        if len(show) > 40:
            print(f"        ... and {len(show) - 40} more")

    if new_total:
        print(f"\n=== FAILED: {new_total} new finding(s). ===")
        print("Fix them, or run --update-baseline if they are a deliberate, reviewed deferral.")
        return 1
    print("\n=== PASSED. ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
