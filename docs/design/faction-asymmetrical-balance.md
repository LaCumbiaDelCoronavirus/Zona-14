# Faction Asymmetrical Balance — Design Doc

**Status:** Draft / proposal · **Scope:** Duty, Freedom, Mercenaries, Military, Ecologists, Bandits
**Goal:** Make the six factions play differently *apart from their weaponry* — through anomaly
resistances, armor profiles, artifacts & their boons, and non-combat traits.
**Foundation:** builds **on top of the existing "Armor v2" system** (`_Zona14`), it does **not** replace it.

---

## 1. Context — this sits on Armor v2, not the old `_Stalker` suits

An in-progress rework ("Armor v2", git `c4f2d1b48d balance(armor): armour v2 stage A - role/tier/plate
tier bases`, plus the bullet-pen rebalance `#30`) already defines the armor framework in
`Resources/Prototypes/_Zona14/Entities/Objects/Clothing/OuterClothing/armor_tiers.yml`. The old
`_Stalker` SEVA reskins are being deprecated (see `_Stalker/ShopPresets/OUTDATED/`). **All faction
work below targets the `_Zona14` bases.** The faction identities are the layer Armor v2 does *not*
yet encode.

### Armor v2 in one screen (verified against the file)

Three independent axes:

- **ROLE** — `PvP` (fights people/mutants) vs `PvE` (survives the Zone) vs neutral.
- **TIER** — 1–5, drives every number via `coeff = 1 − Tier×0.10`.
- **PLATE** — `armorClass`, **set per item, decoupled from tier**. A T5 SEVA can be plate 0–1; a T5
  combat suit is plate 5. Plate governs **bullet penetration only** (below).

Base formula:

| | phys coeff (Blunt/Slash/Pierce) | elem coeff (Heat/Cold/Shock/Rad/Caustic/Compr/Psy) | phys flat | elem flat | artifact slots |
|---|---|---|---|---|---|
| **PvP** | `1 − 0.1T − 0.1` (better) | `1 − 0.1T + 0.1` (worse) | `2T` | `1T` | `T` |
| **PvE** | `1 − 0.1T + 0.1` (worse) | `1 − 0.1T − 0.1` (better) | `1T` | `2T` | `T + 1` |
| neutral | `1 − 0.1T` | `1 − 0.1T` | `2T` | `1T` | `T` |

Two landmines the file itself flags — **do not trip these**:
1. **"No plates" is `armorClass: 0`, NEVER an absent `armorClass`.** `BuildPenetrationDict` only
   penetrates a piece when `ArmorClass.HasValue`; a null class is *never* penetrated and becomes the
   strongest armor in the game.
2. **T5 PvP at plate 5 already sits at the 25% projectile damage floor** vs standard rifle ammo. No
   coefficient/flat can go lower — making heavy armor tankier means moving
   `playtest.min_projectile_damage_floor` (a global dial). (This is why a T6 tier was dropped.)

Elemental flats are calibrated so **matched-tier armor exactly survives its tier's ambient
`MapRadiation` zone** (ticks just below `Tier×1`). ⚠ **Any per-faction elemental nerf must still
clear its tier's MapRadiation survival floor**, or that faction can't stand in its own tier's zone.

---

## 2. Damage model & TTK (verified in code)

**Per hit, for every worn armor piece** (no hit locations — all worn armor applies to every hit;
coefficients multiply, flat reductions add):

```
final = max(0, raw*projMod − flat) × coeff          # flat first, THEN coefficient
```

**Tier is enforced via penetration** — `classDiff = ammoClass(projectileClass) − plate(armorClass)`:

| classDiff (ammo − plate) | Penetration (current CVar) | Effect |
|---|---|---|
| ≤ −1 (ammo below plate) | `0.0` | armor at **full** strength |
| 0 (matched) | `0.5` | armor halved |
| +1 | `0.75` | armor mostly bypassed |
| ≥ +2 | `0.9` | armor almost ignored |

Applied as `coeff' = coeff + (1−coeff)·pen`, `flat' = flat·(1−pen)`. Plus a **damage floor**: every
bullet deals **≥ `min_projectile_damage_floor` × (raw·projMod)** (default 0.25). Global dial:
`playtest.projectile_damage_modifier` (default 1.0). **Health: Critical/downed = 100, Dead = 200.**
Ammo class tracks **penetration, not raw damage** (rifle rounds are ~26–35 Piercing across classes).

### TTK target & the LOCKED fix (from `ttk_calculator.py`)

**Design decision:** **matched = 15 bullets to DOWN (crit @ 100) at *every* tier** (T1v1 = T5v5 = 15),
with a **big, harsh cross-tier spread**: a T5 dunks a T1 in the **minimum 6 bullets**, and a T1 needs
**~30** on a T5. Tier matters a lot in PvP, but same-tier fights are always a fair 15.

**Why the current system fights this:** at live defaults, matched T3-vs-T3 is ~5 bullets and gaps are
decisive-but-random (armor grows with tier, ammo doesn't, penetration swings `0.0 → 0.9`).

**The fix — scale BOTH armor and ammo with tier so they cancel at matched but not across tiers:**
1. **Armor physical (bullet) coeff scales with tier:** `0.86 / 0.73 / 0.60 / 0.47 / 0.34` (T1→T5),
   flats `1 / 1.5 / 2 / 2.5 / 3`. (Elemental keeps its own steep tier scaling; role offset still
   applies — PvE/SEVA a bit worse vs bullets = the anomaly-suit fragility.)
2. **Ammo Piercing scales with tier:** `22 / 26 / 31 / 38 / 44` (T1→T5). *(This is the extra work —
   an ammo pass so each round's damage tracks its class; current ammo is ~26–35 and roughly flat.)*
3. **Global dials:** `projectile_damage_modifier 0.40`, `min_projectile_damage_floor 0.38` (caps the
   defender extreme ~30), penetration `below 0.05 / match 0.10 / above1 0.48 / above2 0.92`.

**Result (combat-suit vs combat-suit, bullets to crit):**

```
                 attacker ammo →  T1   T2   T3   T4   T5
  defender T1:                    15   11    9    7    6
  defender T2:                    19   15   11    7    6
  defender T3:                    24   19   15    9    6
  defender T4:                    30   26   21   15    9
  defender T5:                    30   26   22   18   15
```
Matched **15** at every tier; **minimum 6** (T5→T1); **max ~30** (T1→T5). Smooth, monotonic. Full
death (200) ≈ 2×.

**Caveats — playtest before committing:** models the *combat* suit (plate = tier); a SEVA/low-plate
anomaly suit is *intentionally* more bullet-fragile (its good coeff gets penetrated away). Models the
outer suit only (a full kit raises real TTK). Validate with `BalanceHelperSystem` CSV + playtest.

> These are **game-wide lethality** changes (all players, all guns): armor formula + an ammo pass +
> CVars. Big blast radius — implement as its own pass and playtest before merge.

---

## 3. Faction asymmetry, expressed on Armor v2

Faction identity is a **selection over Armor v2 levers**, not a new coefficient system:

| Lever | How factions differ |
|---|---|
| **Role lean** (PvP/PvE) | which suits a faction fields & sells |
| **Plate** (`armorClass`) | bullet survivability — decoupled from tier |
| **Tier access** | which tiers the faction's shop sells (economy-gated) |
| **Artifact slots** | PvE gives `T+1`; per-faction overrides (Duty = 0) |
| **Economy** | shop prices / buy-sell rates |
| **Flagship per-type override** (Hybrid) | on signature suits only, override specific elemental types |

Per the agreed **Hybrid** approach: everyone rides the uniform elemental formula; only each faction's
**flagship suit** gets per-anomaly-type overrides — kept legible and MapRadiation-safe.

| Faction | Role lean | Plate | Tier access | Artifact slots | Economy | Flagship per-type override |
|---|---|---|---|---|---|---|
| **Duty** | PvP | **high (= tier)** | T2–T5 | **0** (override + job block) | state logistics; cheap armor repair | Heavy suit: bake **Heat/Caustic/Rad** up so it survives deep Zone with no artifacts; leave **Psy** at PvP-weak default (soft spot) |
| **Military** | PvP | **highest** + best `ExplosionResistance` | T2–T5 | `T−1` (distrust) | cheapest ammo/ballistic | none — stays Zone-blind (PvP-weak elemental) |
| **Mercs** | neutral | mid | T1–T5 (widest) | `T` | **best trade rates** | none |
| **Freedom** | PvE-lean | **low (1–2)** | T2–T5 | `T+1` (high) | cheap detectors | slight **Rad** edge (deep-Zone dwellers) |
| **Ecologists** | PvE | **0–1 (lowest)** | T3 SEVA peak (+some T4–5) | `T+1` (high) | best detectors, medical, rad-purge | SEVA: best-in-game **Psy / Rad / Caustic** |
| **Bandits** | neutral / PvP-lite | low | **T1–T3 only, cheapest** | `T−1` (few) | **cheapest resupply + best artifact sell** | none |

Why this works — **plate is decoupled from tier**, so the two "tank" and two "Zone" fantasies stay
distinct even at the same tier:
- **Duty vs Military** — both high plate (bullet tanks), but Duty bakes elemental (deep-Zone
  self-sufficient, no artifacts, Psy-weak) while Military stays Zone-blind with the best ballistic +
  blast. Different tanks.
- **Ecologists vs Freedom** — both PvE / low-plate / high-slot artifact-leaners, but Ecologists peak
  on specialized elemental (Psy/Rad/Caustic) + detection/medical, while Freedom trades that for the
  best **mobility** and a touch more plate ("not paper"). Different casters.
- **Mercs** = balanced/economy flex; **Bandits** = cheap disposable swarm capped at low tier.

### Rock-paper-scissors

- **Open firefight** → Military ≥ Duty ≫ Ecologist/Freedom (plate decides bullets)
- **Mutant melee swarm** → Duty ≫ everyone (best Blunt/Slash; mutants deal `Slash`)
- **Deep anomaly field (psy/rad/chem)** → Ecologist ≫ Duty > Freedom; Military & Bandits die
- **Psy fields** → Ecologist (and slotted Freedom) > everyone; **Duty's one soft spot**
- **Attrition / economy** → Bandits & Mercs outlast on cheap resupply

---

## 4. The Duty artifact ban (firm lore rule)

Two layers so it can't be bypassed by looting an enemy suit:
1. **`GrantsArtifactSlots: 0`** override on Duty-exclusive suits (overriding the PvP `T` default).
2. **Job-level block component** via `AddComponentSpecial` on Duty jobs — precedent: `dolg.yml`
   already adds `BlockTackingHolyItems` this way. A parallel `BlockArtifactUsage` makes it hold
   regardless of worn suit.

**Compensation (P2 — fewer slots ⇒ more baked resistance):**
- *Now:* the flagship-suit **Heat/Caustic/Rad overrides** (§3) are the payback — Duty is the one
  faction whose deep-Zone survival is fully baked into the suit. Plus one small always-on passive
  ("doesn't go down easy": minor bleed-resist / slow regen) to stand in for artifact healing.
- *Later (your mutant-parts idea):* repurpose Duty's slots as **trophy/gadget slots** taking mutant
  parts (pelts/hooves) or crafted gadgets — reuses items already in the Duty shop + `PersistentCrafting`.
  Don't block v1 on it.

---

## 5. Soft-lock: "penalty for non-members" gear

Anyone can wear any suit, but full perks require membership; outsiders get a penalty, not a block.
**Feasible:** `FactionClothingSystem` already hooks `GotEquipped/Unequipped` + `_faction.IsMember`.
A sibling `STFactionGear` component applies a member-only bonus / non-member malus.

| Suit | Member perk | Non-member penalty | Lever |
|---|---|---|---|
| **Duty** heavy | normal `STWeight` | **+15–20 weight** (slower) | `STWeight` |
| **Freedom** light | sprint bonus | no speed bonus | `ClothingSpeedModifier` |
| **Ecologist** SEVA | full elemental | degraded elemental | resistance* |
| **Military** | full blast + normal weight | heavier, no blast bonus | `STWeight`/`ExplosionResistance` |
| **Merc / Bandit** | — | ~none (universal gear — on-theme) | — |

\* conditional **speed/weight/slots** is easy (runtime modifiers); conditional **resistance** needs a
modifier-set swap on equip — treat as advanced, not v1.

---

## 6. Feasibility & rollout

| Change | Cost |
|---|---|
| Faction role/plate/tier/slot selection on the `_Zona14` bases | **Pure YAML** |
| Flagship per-type elemental overrides (MapRadiation-checked) | **Pure YAML** |
| Per-faction shop catalog/pricing (incl. cheap Bandit, Duty repair) | **Pure YAML** |
| Duty artifact ban | **Small component** (mirror `BlockTackingHolyItems`) |
| Soft-lock speed/weight/slot perks | **Small component** (mirror `FactionClothingSystem`) |
| Duty "doesn't go down easy" passive | **Small component** |
| Global TTK dials (projMod / floor / pen CVars) | **CVar tuning** — game-wide, playtest first |
| Conditional resistance perk; Duty trophy slots | **Advanced / later** |

**Rollout (lowest-risk first):**
1. **Global TTK pass** (separate from factions, own PR) — three parts per §2: (a) scale armor
   **physical** coeff/flat with tier in `armor_tiers.yml`; (b) **ammo pass** — scale each round's
   Piercing with its class (`22→44`); (c) CVars `projMod 0.40`, `floor 0.38`, pen `0.05/0.10/0.48/0.92`.
   Verify with `ttk_calculator.py` + `BalanceHelperSystem` + playtest → matched 15 every tier, min 6.
2. **Artifact-slot pass** — per-faction slot values + Duty block. Tiny, biggest identity signal.
3. **Faction suit pass** — assign each faction's suits to the right Armor v2 base (role/plate/tier);
   add flagship overrides. Pure YAML, reversible.
4. **Shop pass** — per-faction catalog & pricing.
5. **Mobility/carry + soft-lock component.**
6. **Duty passive; later Phase-2 trophy slots.**

---

## 7. Open questions

- **RESOLVED — gunfight TTK:** matched **15 at every tier**; big harsh spread (**min 6** T5→T1,
  **~30** T1→T5). Achieved by scaling armor coeff + ammo Piercing + CVars (§2). Still needs playtest
  to confirm it feels right with full kits + the real per-caliber ammo spread.
- Elemental/anomaly protection keeps steep tier scaling — confirm the MapRadiation survival-by-tier
  math still lines up after the physical/elemental split.
- Freedom & Ecologist both high-tier/low-plate PvE — is the mobility-vs-specialization split enough
  to keep them distinct, or give Freedom its own tier cap?
- Exact non-member `STWeight` penalty (slow, not immobilize).
- Bandit artifact slots: `T−1`, or a flat cap of 2?

---

*Tooling:* `docs/design/ttk_calculator.py` models the verified pipeline; pair with
`Content.Server/_Stalker/BalanceHelper/BalanceHelperSystem.cs` CSV dumps for real-suit validation.
