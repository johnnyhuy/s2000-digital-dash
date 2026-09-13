// =============================================================================
// 2D OEM silhouette + window helpers (replace-face, arc lock)
// =============================================================================
// Same maths as src/face_spec.py / gauge_ui.py hood_outer_points(): the hood
// is a circular crown (crown_c, crown_r) springing from a flat lower bezel;
// the tach is a bar graph on a true circular arc (tach_c, r_out .. r_in).
// All millimetre sizes are still ESTIMATED — see dims.scad.
// =============================================================================

include <dims.scad>

// Points along a circle (mm) between two screen angles.
function arc_pts(c, r_mm, deg0, deg1, n = arc_steps) =
    [for (i = [0 : n]) on_circle(c, r_mm, deg0 + (deg1 - deg0) * i / n)];

// Screen angles where a crown circle of radius r meets the spring line
// (right spring first, sweeping over the top to the left).
function crown_angles(r_frac) =
    let (
        half = crown_half(r_frac),
        dy = crown_c[1] - spring_y             // screen-space dy (spring above centre → negative)
    )
    [atan2(dy, half), atan2(dy, -half)];

// Crown arc in mm from the right spring, over the peak, to the left spring.
function crown_arc(r_frac) =
    let (a = crown_angles(r_frac)) arc_pts(crown_c, W(r_frac), a[0], a[1]);

// Counter-clockwise from bottom-left: flat bottom, up the right side to the
// spring, over the hood crown (crown + lip), down the left side.
function hood_points() =
    let (arc = crown_arc(crown_r + crown_lip))
    concat(
        [[0, 0], [face_w, 0], [face_w, spring_y], arc[0]],
        arc,
        [arc[len(arc) - 1], [0, spring_y]]
    );

// Black face aperture: crown inner edge over the top, full width (minus the
// lip) below the spring.
function aperture_points() =
    let (arc = crown_arc(crown_r), lip = W(crown_lip))
    concat(
        [[face_w - lip, lip], [face_w - lip, spring_y], arc[0]],
        arc,
        [arc[len(arc) - 1], [lip, spring_y], [lip, lip]]
    );

module hood_2d() { polygon(hood_points()); }
module aperture_2d() { polygon(aperture_points()); }

module stadium_2d(w, h) {
    r = min(w, h) / 2;
    hull() {
        translate([r, r]) circle(r = r);
        translate([w - r, r]) circle(r = r);
        translate([r, h - r]) circle(r = r);
        translate([w - r, h - r]) circle(r = r);
    }
}

module rounded_rect_2d(w, h, r) {
    rr = min(r, w / 2, h / 2);
    hull() {
        translate([rr, rr]) circle(r = rr);
        translate([w - rr, rr]) circle(r = rr);
        translate([rr, h - rr]) circle(r = rr);
        translate([w - rr, h - rr]) circle(r = rr);
    }
}

module rect_mm_2d(r, radius = 0) {
    m = rect_mm(r);
    translate([m[0], m[1]]) rounded_rect_2d(m[2], m[3], radius);
}

// Annular sector between two radii (fractions of module width) and two
// screen angles — the display shows the band, ticks and numerals through it.
module sector_2d(r_hi, r_lo, deg0, deg1) {
    outer = arc_pts(tach_c, W(r_hi), deg0, deg1);
    inner = arc_pts(tach_c, W(r_lo), deg1, deg0);
    polygon(concat(outer, inner));
}

// One window from just outside the band's outer edge to just inside the
// numerals, spanning the hatch overrun past 0 and 9.
module tach_window_2d() {
    margin = tach_win_margin / face_w;
    over = tach_hatch_deg + 1.5;
    sector_2d(
        tach_r_out + margin,
        tach_r_num - tach_win_num_depth / face_w,
        tach_a0 - over,
        tach_a9 + over
    );
}

module speed_window_2d() { rect_mm_2d(speed_win, lcd_win_r); }
module odo_window_2d() { rect_mm_2d(odo_win, lcd_win_r); }

// TEMP / FUEL windows include the icon above and the C/H or E/F letters.
module temp_window_2d() {
    icon = pt_mm(temp_icon);
    c = pt_mm(temp_c);
    h = pt_mm(temp_h);
    top = icon[1] + W(0.016);
    bot = Y(temp_underline_y) - gauge_pad;
    x0 = c[0] - W(0.012) - gauge_pad;
    x1 = h[0] + W(0.012) + gauge_pad;
    translate([x0, bot]) rounded_rect_2d(x1 - x0, top - bot, 1.2);
}

module fuel_window_2d() {
    icon = pt_mm(fuel_icon);
    e = pt_mm(fuel_e);
    f = pt_mm(fuel_f);
    top = icon[1] + W(0.015);
    bot = Y(fuel_underline_y) - gauge_pad;
    x0 = e[0] - W(0.012) - gauge_pad;
    x1 = f[0] + W(0.012) + gauge_pad;
    translate([x0, bot]) rounded_rect_2d(x1 - x0, top - bot, 1.2);
}

module arc_lamp_holes_2d(clear = arc_lamp_hole_clear) {
    for (l = arc_lamps)
        translate(pt_mm(l)) circle(r = W(arc_lamp_r) + clear);
}

module strip_window_2d(pad = strip_pad) {
    m = rect_mm(strip);
    translate([m[0] - pad, m[1] - pad]) rounded_rect_2d(m[2] + 2 * pad, m[3] + 2 * pad, 2.0);
}

module panel_windows_2d() {
    if (len(panel_left) == 4) rect_mm_2d(panel_left, 1.0);
    if (len(panel_right) == 4) rect_mm_2d(panel_right, 1.0);
}

// Every window is clipped to the hood inset by min_rim so the mask keeps a
// printable / laser-safe rim where the band runs under the crown lip.
module display_windows_2d() {
    intersection() {
        union() {
            tach_window_2d();
            speed_window_2d();
            odo_window_2d();
            temp_window_2d();
            fuel_window_2d();
            arc_lamp_holes_2d();
            strip_window_2d();
            panel_windows_2d();
        }
        offset(delta = -min_rim) hood_2d();
    }
}

// --- hardware -------------------------------------------------------------------
module rocker_2d(extra = 0) {
    translate([btn_minus_c[0] - btn_d_mm / 2 - extra, btn_minus_c[1] - btn_d_mm / 2 - extra])
        stadium_2d(rocker_w + 2 * extra, rocker_h + 2 * extra);
}

module oval_2d(c, extra = 0) {
    translate([c[0] - oval_w_mm / 2 - extra, c[1] - oval_h_mm / 2 - extra])
        stadium_2d(oval_w_mm + 2 * extra, oval_h_mm + 2 * extra);
}

module button_caps_2d(extra = 0) {
    rocker_2d(extra);
    oval_2d(btn_sel_c, extra);
    oval_2d(btn_trip_c, extra);
}

function stem_xy() = [btn_minus_c, btn_plus_c, btn_sel_c, btn_trip_c];

// Four PLACEHOLDER alignment pins in the lower bezel corners — fiction until measured.
function align_xy() = [
    [W(0.035), 3.0],
    [face_w - W(0.035), 3.0],
    [W(0.035), spring_y - 3.0],
    [face_w - W(0.035), spring_y - 3.0]
];

module align_holes_2d(d = align_hole_d) {
    for (p = align_xy()) translate(p) circle(d = d);
}

// --- panel pocket --------------------------------------------------------------------
module panel_pocket_2d(clear = panel_clear) {
    translate([panel_rect[0] - clear, panel_rect[1] - clear])
        rounded_rect_2d(panel_rect[2] + 2 * clear, panel_rect[3] + 2 * clear, 1.5);
}

module active_area_2d() {
    translate([active_rect[0], active_rect[1]]) square([active_rect[2], active_rect[3]]);
}

function point_in_rect(p, r) =
    p[0] >= r[0] && p[0] <= r[0] + r[2] && p[1] >= r[1] && p[1] <= r[1] + r[3];
