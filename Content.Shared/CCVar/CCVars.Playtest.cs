using Content.Shared.Administration;
using Content.Shared.CCVar.CVarAccess;
using Content.Shared.Roles;
using Robust.Shared.Configuration;

namespace Content.Shared.CCVar;

public sealed partial class CCVars
{
        /// <summary>
        ///     Scales all damage dealt in the game.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestAllDamageModifier =
            CVarDef.Create("playtest.all_damage_modifier", 1f, CVar.SERVER | CVar.REPLICATED);

        /// <summary>
        ///     Scales all healing done in the game.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestAllHealModifier =
            CVarDef.Create("playtest.all_heal_modifier", 1f, CVar.SERVER | CVar.REPLICATED);

        /// <summary>
        ///     Scales the damage dealt by all melee attacks in the game.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestMeleeDamageModifier =
            CVarDef.Create("playtest.melee_damage_modifier", 1f, CVar.SERVER | CVar.REPLICATED);

        /// <summary>
        ///     Scales the damage dealt by all projectiles in the game.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestProjectileDamageModifier =
            CVarDef.Create("playtest.projectile_damage_modifier", 0.40f, CVar.SERVER | CVar.REPLICATED); // Zona14: TTK rework — matched ~15 bullets to down

        /// <summary>
        ///     Scales the damage dealt by all hitscan attacks in the game.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestHitscanDamageModifier =
            CVarDef.Create("playtest.hitscan_damage_modifier", 1f, CVar.SERVER | CVar.REPLICATED);

        /// <summary>
        ///     Scales the damage dealt by all thrown weapons in the game.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestThrownDamageModifier =
            CVarDef.Create("playtest.thrown_damage_modifier", 1f, CVar.SERVER | CVar.REPLICATED);

        /// <summary>
        ///     Scales the healing given by all topicals in the game.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestTopicalsHealModifier =
            CVarDef.Create("playtest.topicals_heal_modifier", 1f, CVar.SERVER | CVar.REPLICATED);

        /// <summary>
        ///     Scales the damage dealt by all reagents in the game.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestReagentDamageModifier =
            CVarDef.Create("playtest.reagent_damage_modifier", 1f, CVar.SERVER | CVar.REPLICATED);

        /// <summary>
        ///     Scales the healing given by all reagents in the game.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestReagentHealModifier =
            CVarDef.Create("playtest.reagent_heal_modifier", 1f, CVar.SERVER | CVar.REPLICATED);

        /// <summary>
        ///     Scales the explosion damage dealt in the game.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestExplosionDamageModifier =
            CVarDef.Create("playtest.explosion_damage_modifier", 1f, CVar.SERVER | CVar.REPLICATED);

        /// <summary>
        ///     Scales the damage dealt to mobs in the game (i.e. entities with MobStateComponent).
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestMobDamageModifier =
            CVarDef.Create("playtest.mob_damage_modifier", 1f, CVar.SERVER | CVar.REPLICATED);

        /// <summary>
        ///     Scales the stamina damage dealt the game.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestStaminaDamageModifier =
            CVarDef.Create("playtest.stamina_damage_modifier", 1f, CVar.SERVER | CVar.REPLICATED);

        // Zona14: armor penetration tier CVars
        /// <summary>
        ///     Penetration fraction when projectile class is below armor class (classDiff ≤ −1). 0 = full armor.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestPenTierBelow =
            CVarDef.Create("playtest.pen_tier_below", 0.05f, CVar.SERVER | CVar.REPLICATED); // Zona14: TTK rework

        /// <summary>
        ///     Penetration fraction when projectile class matches armor class (classDiff = 0).
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestPenTierMatch =
            CVarDef.Create("playtest.pen_tier_match", 0.10f, CVar.SERVER | CVar.REPLICATED); // Zona14: TTK rework

        /// <summary>
        ///     Penetration fraction when projectile is one tier above armor (classDiff = 1).
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestPenTierAboveOne =
            CVarDef.Create("playtest.pen_tier_above_one", 0.48f, CVar.SERVER | CVar.REPLICATED); // Zona14: TTK rework

        /// <summary>
        ///     Penetration fraction when projectile is two+ tiers above armor (classDiff ≥ 2).
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestPenTierAboveTwo =
            CVarDef.Create("playtest.pen_tier_above_two", 0.92f, CVar.SERVER | CVar.REPLICATED); // Zona14: TTK rework

        /// <summary>
        ///     Minimum damage floor as a fraction of original damage. Blunt supplement tops up if armor reduces below this.
        /// </summary>
        [CVarControl(AdminFlags.VarEdit)]
        public static readonly CVarDef<float> PlaytestMinProjectileDamageFloor =
            CVarDef.Create("playtest.min_projectile_damage_floor", 0.38f, CVar.SERVER | CVar.REPLICATED); // Zona14: TTK rework — caps T1-vs-T5 ~30
        // End Zona14

}
