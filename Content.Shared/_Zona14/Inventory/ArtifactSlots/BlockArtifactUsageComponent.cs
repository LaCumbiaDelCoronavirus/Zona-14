using Robust.Shared.GameStates;

namespace Content.Shared._Zona14.Inventory.ArtifactSlots;

/// <summary>
/// Placed on a mob (typically via a job's AddComponentSpecial) to forbid it from ever
/// equipping items into artifact slots — a hard, suit-independent artifact ban.
/// Used for the Duty faction, whose lore forbids artifact use entirely: the ban holds
/// even if the member loots and wears another faction's slot-granting suit.
/// Mirrors the marker-component + attempt-cancel pattern of BlockTackingHolyItems.
/// </summary>
[RegisterComponent, NetworkedComponent]
public sealed partial class BlockArtifactUsageComponent : Component
{
}
