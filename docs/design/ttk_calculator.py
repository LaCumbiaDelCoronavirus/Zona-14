#!/usr/bin/env python3
"""
Zona-14 TTK model of record — models the REAL damage pipeline (verified in code, 2026-07).

Pipeline (per hit, per worn armor piece):
    final = max(0, raw*projMod - flat) * coeff          # flat first, then coeff (DamageSpecifier.ApplyModifierSet)
Tier penetration (BuildPenetrationDict / BuildPenetratedModifiers, ProjectileSystem):
    classDiff = ammoClass(projectileClass) - armorPlate(armorClass)
    pen = {<=-1: below, 0: match, +1: above1, >=+2: above2}      # playtest.pen_tier_* CVars
    coeff' = coeff + (1-coeff)*pen ;  flat' = flat*(1-pen)
Damage floor:  bullet always deals >= floor * (raw*projMod)       # playtest.min_projectile_damage_floor
Global dial:   projMod = playtest.projectile_damage_modifier
Health:  Critical/downed = 100 ,  Dead = 200.

DESIGN (locked): matched (Tn ammo vs Tn armor) = 15 to DOWN at EVERY tier; big T1<->T5 spread.
  minimum kill = 6 (T5 ammo vs T1 armor);  T1 ammo vs T5 armor = ~31 (floor-capped).
Achieved by scaling BOTH armor AND ammo with tier so they cancel at matched but not across tiers.
"""
import math

# ---- locked global dials ----
PROJMOD = 0.40
FLOOR   = 0.38
PEN = dict(below=0.05, match=0.10, above1=0.48, above2=0.92)

# ---- locked per-tier tables ----
# armor physical (Blunt/Slash/Piercing) — PvP/combat suit; plate (armorClass) = tier
ARMOR_COEFF = {1: 0.86, 2: 0.73, 3: 0.60, 4: 0.47, 5: 0.34}
ARMOR_FLAT  = {1: 1.0,  2: 1.5,  3: 2.0,  4: 2.5,  5: 3.0}
# ammo Piercing (raw, pre-armor) by tier/projectileClass  (current game ammo ~26-35, roughly flat)
AMMO_RAW    = {1: 22,   2: 26,   3: 31,   4: 38,   5: 44}

def pen(class_diff):
    return PEN['below'] if class_diff <= -1 else PEN['match'] if class_diff == 0 else \
           PEN['above1'] if class_diff == 1 else PEN['above2']

def per_bullet(def_tier, atk_tier):
    coeff, flat, raw = ARMOR_COEFF[def_tier], ARMOR_FLAT[def_tier], AMMO_RAW[atk_tier]
    p = pen(atk_tier - def_tier)                 # plate = tier
    ce = coeff + (1 - coeff) * p
    fe = flat * (1 - p)
    R = raw * PROJMOD
    return max(max((R - fe) * ce, 0.0), FLOOR * R)

def bullets(def_tier, atk_tier, thr=100):
    return math.ceil(thr / per_bullet(def_tier, atk_tier))

if __name__ == "__main__":
    print(f"projMod={PROJMOD} floor={FLOOR} pen={PEN}")
    print("armor coeff T1..T5 = " + ", ".join(f"{ARMOR_COEFF[t]:.2f}" for t in range(1, 6)) +
          " | flat = " + ", ".join(f"{ARMOR_FLAT[t]:.1f}" for t in range(1, 6)))
    print("ammo  raw   T1..T5 = " + ", ".join(f"{AMMO_RAW[t]}" for t in range(1, 6)))
    print("\nbullets to DOWN(crit 100) — DEFENDER armor (rows) vs ATTACKER ammo (cols)")
    print("               atk ->  T1   T2   T3   T4   T5")
    for dt in range(1, 6):
        row = " ".join(f"{bullets(dt, at):>4}" for at in range(1, 6))
        print(f"  defender T{dt}:    {row}")
    print("\n  matched diagonal: " + ", ".join(str(bullets(t, t)) for t in range(1, 6)) + "  (target 15)")
    print(f"  min (T5 ammo vs T1 armor): {bullets(1, 5)}   max (T1 ammo vs T5 armor): {bullets(5, 1)}")
