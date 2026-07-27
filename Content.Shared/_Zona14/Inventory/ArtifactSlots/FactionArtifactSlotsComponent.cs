using Robust.Shared.GameStates;

namespace Content.Shared._Zona14.Inventory.ArtifactSlots;

/// <summary>
/// Placed on a mob (typically via a job's AddComponentSpecial) to grant a baseline number
/// of artifact slots tied to the mob's faction rather than to any worn suit. This expresses
/// each faction's flat artifact-slot identity (e.g. Mercenaries 4, Freedom 5) independent of
/// which armour the member happens to wear.
///
/// It acts as a <b>floor</b>: <see cref="SharedArtifactSlotSystem"/> takes the maximum of this
/// value and any equipped <see cref="GrantsArtifactSlotsComponent"/>, so a stronger slot-granting
/// suit can still raise the count, but the member never drops below their faction baseline.
/// </summary>
[RegisterComponent, NetworkedComponent]
public sealed partial class FactionArtifactSlotsComponent : Component
{
    /// <summary>
    /// The baseline number of artifact slots this faction grants its members.
    /// </summary>
    [DataField(required: true)]
    public int Slots;
}
