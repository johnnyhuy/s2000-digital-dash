// =============================================================================
// PLACEHOLDER — stacked preview (Option 1 replace-face, arc lock)
// =============================================================================
// F5 preview only — do not export a combined STL (multi-body).
// Explode is millimetres of air between layers — not a fit claim.
// `-D print_placement=true` echoes part offsets for mesh_export.py.
// =============================================================================

include <parts.scad>

explode = 14;   // set 0 for a closed stack
print_placement = false;

if (print_placement) echo_placement(explode);
else assembly(explode);
