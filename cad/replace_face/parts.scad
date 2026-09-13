// =============================================================================
// 3D printable modules — Option 1 replace-face stack (arc lock)
// =============================================================================
// One module = one solid. The stack, front to rear:
//   rubber buttons → acrylic mask (display windows) → 7" AMOLED in the tray
//   pocket → tray floor. Callipers UNKNOWN. Not a verified AP1 drop-in.
//
// Cabin-facing hard parts: PETG or ASA. Do NOT use PLA in the cabin.
// Buttons: TPU 95A or cast silicone — not OEM rubber.
// =============================================================================

include <outline.scad>

module _through(h) {
    translate([0, 0, -eps])
        linear_extrude(h + 2 * eps)
            children();
}

// Tray outline: the hood silhouette plus the panel envelope (the 7" module is
// taller than the face, so the tray grows behind the hood to hold it).
module _tray_2d() {
    offset(delta = wall) {
        hood_2d();
        panel_pocket_2d();
    }
}

module backlight() {
    // Tray shell — one difference. The outer rim is a print wall, NOT a
    // measured bay clip and NOT a claimed AP1 fit.
    difference() {
        linear_extrude(tray_h)
            _tray_2d();

        // Face rebate: the mask drops in flush with the tray top.
        translate([0, 0, face_rebate_z])
            linear_extrude(face_t + 1)
                offset(delta = face_pocket_clear)
                    hood_2d();

        // 7" panel pocket, glass toward the mask.
        translate([0, 0, panel_z])
            linear_extrude(face_rebate_z - panel_z + eps)
                panel_pocket_2d();

        // Cavity under the panel for the driver board / cables.
        translate([0, 0, floor_t])
            linear_extrude(panel_z - floor_t + eps)
                offset(delta = -wall)
                    panel_pocket_2d();

        // Switch wells — only where they miss the panel; switch model UNKNOWN.
        for (p = stem_xy())
            if (!point_in_rect(p, panel_rect))
                translate([p[0], p[1], -eps])
                    cylinder(h = stem_well_h + eps, d = stem_well_d);

        // Panel FPC tail — LOCATION UNKNOWN (bottom-centre guess).
        translate([panel_c[0] - panel_tail_w / 2, panel_rect[1] - wall - panel_clear - eps, panel_z - panel_tail_h])
            cube([panel_tail_w, wall + panel_clear + 2 * eps, panel_tail_h + panel_t]);

        // Driver-board cable escape — LOCATION UNKNOWN.
        translate([face_w / 2 - cable_w / 2, panel_rect[1] - wall - panel_clear - eps, floor_t])
            cube([cable_w, wall + panel_clear + 2 * eps, cable_h]);

        _through(tray_h)
            align_holes_2d();
    }
}

module _cowl_web_2d() {
    // Light-baffle web between the display windows. Sits on the panel glass
    // under the mask so adjacent windows do not bleed into each other.
    difference() {
        offset(delta = -0.45) aperture_2d();
        offset(delta = 0.35) display_windows_2d();
        button_caps_2d(1.2);
        align_holes_2d(align_hole_d + 0.8);
    }
}

module backlight_web() {
    // Separate baffle insert — one extrusion, same thickness as the mask gap.
    linear_extrude(web_t - 0.1)
        _cowl_web_2d();
}

module acrylic_face() {
    // Mask plate — through-windows only. The display shows the bar-graph tach,
    // numerals, LCD windows, side gauges and telltales through them; the
    // cowl, lower bezel, PUSH CANCEL and mph·km/h legends stay printed.
    difference() {
        linear_extrude(face_t) hood_2d();
        _through(face_t) display_windows_2d();
        _through(face_t) button_caps_2d(button_clear);
        _through(face_t) align_holes_2d();
    }
}

module _button_solid(w, h, flange_extra) {
    // Single hull: cap → flange. No stem (switch UNKNOWN — add after measure).
    hull() {
        linear_extrude(eps) stadium_2d(w, h);
        translate([0, 0, button_cap_t - eps])
            linear_extrude(eps) stadium_2d(w, h);
        translate([-flange_extra, -flange_extra, button_cap_t + button_flange_t - eps])
            linear_extrude(eps) stadium_2d(w + 2 * flange_extra, h + 2 * flange_extra);
    }
}

module rocker_button() {
    // −/+ pair as one rocker cap (push = CANCEL). Local origin bottom-left.
    difference() {
        _button_solid(rocker_w, rocker_h, button_flange_extra);
        translate([rocker_w / 2 - rocker_groove_w / 2, -eps, -eps])
            cube([rocker_groove_w, rocker_h + 2 * eps, rocker_groove_d + eps]);
    }
}

module oval_button() {
    _button_solid(oval_w_mm, oval_h_mm, min(button_flange_extra, 1.0));
}

module sel_button() { oval_button(); }
module trip_button() { oval_button(); }

module rubber_buttons_print() {
    // F5 plate preview only — do not export this as one STL.
    rocker_button();
    translate([rocker_w + 8, 0, 0]) sel_button();
    translate([rocker_w + 8 + oval_w_mm + 8, 0, 0]) trip_button();
}

module rubber_buttons_placed() {
    translate([0, 0, button_cap_t * 0.35])
        mirror([0, 0, 1]) {
            translate([btn_minus_c[0] - btn_d_mm / 2, btn_minus_c[1] - btn_d_mm / 2, 0]) rocker_button();
            translate([btn_sel_c[0] - oval_w_mm / 2, btn_sel_c[1] - oval_h_mm / 2, 0]) sel_button();
            translate([btn_trip_c[0] - oval_w_mm / 2, btn_trip_c[1] - oval_h_mm / 2, 0]) trip_button();
        }
}

module panel_placeholder() {
    // F5 preview only — the bought 7" module, not a printable.
    translate([panel_rect[0], panel_rect[1], 0])
        cube([panel_rect[2], panel_rect[3], panel_t]);
    color([0.05, 0.05, 0.06])
        translate([active_rect[0], active_rect[1], panel_t])
            cube([active_rect[2], active_rect[3], 0.1]);
}

// Assembly placement for mesh_export.py — one ECHO line per part, mm.
// `openscad -o /dev/null -D print_placement=true assembly.scad`
module echo_placement(explode = 0) {
    echo(place = ["backlight", 0, 0, 0]);
    echo(place = ["panel", 0, 0, panel_z + explode * 0.5]);
    echo(place = ["backlight_web", 0, 0, panel_z + panel_t + explode]);
    echo(place = ["acrylic_face", 0, 0, face_rebate_z + explode * 1.6]);
    // Buttons: local origin bottom-left; placed cap-down onto the mask.
    bz = tray_h + explode * 2.4;
    echo(place = ["button_rocker", btn_minus_c[0] - btn_d_mm / 2, btn_minus_c[1] - btn_d_mm / 2, bz]);
    echo(place = ["button_sel", btn_sel_c[0] - oval_w_mm / 2, btn_sel_c[1] - oval_h_mm / 2, bz]);
    echo(place = ["button_trip", btn_trip_c[0] - oval_w_mm / 2, btn_trip_c[1] - oval_h_mm / 2, bz]);
    echo(panel_box = [panel_rect[0], panel_rect[1], panel_rect[2], panel_rect[3], panel_t]);
}

module assembly(explode = 0) {
    // F5 preview only. Not a printable mesh.
    color([0.22, 0.22, 0.24]) backlight();
    color([0.12, 0.14, 0.18])
        translate([0, 0, panel_z + explode * 0.5]) panel_placeholder();
    color([0.55, 0.52, 0.48])
        translate([0, 0, panel_z + panel_t + explode]) backlight_web();
    color([0.82, 0.80, 0.74, 0.55])
        translate([0, 0, face_rebate_z + explode * 1.6]) acrylic_face();
    color([0.12, 0.12, 0.12])
        translate([0, 0, tray_h + explode * 2.4]) rubber_buttons_placed();
}
