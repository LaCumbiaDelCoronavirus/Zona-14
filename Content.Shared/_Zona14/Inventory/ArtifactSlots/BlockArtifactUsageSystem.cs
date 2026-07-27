using Content.Shared.Inventory.Events;

namespace Content.Shared._Zona14.Inventory.ArtifactSlots;

/// <summary>
/// Enforces <see cref="BlockArtifactUsageComponent"/>: cancels any attempt to equip an
/// item into an artifact slot on a mob that carries the component. Because it keys off the
/// wearer rather than the suit, the Duty artifact ban holds regardless of the worn armour.
/// </summary>
public sealed class BlockArtifactUsageSystem : EntitySystem
{
    public override void Initialize()
    {
        base.Initialize();

        SubscribeLocalEvent<BlockArtifactUsageComponent, IsEquippingTargetAttemptEvent>(OnEquipTargetAttempt);
    }

    private void OnEquipTargetAttempt(Entity<BlockArtifactUsageComponent> ent, ref IsEquippingTargetAttemptEvent args)
    {
        if (args.Cancelled)
            return;

        if (!args.SlotFlags.HasFlag(SlotFlags.ARTIFACT))
            return;

        args.Reason = "artifact-usage-blocked";
        args.Cancel();
    }
}
