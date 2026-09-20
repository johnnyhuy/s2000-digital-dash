// Digital-screen bench setup. Millimetres; +Z faces the driver.
// Panel and housing dimensions are provisional, NOT a measured vehicle fit.
// Pi PCB outline / hole centres: Raspberry Pi 5 mechanical drawing (see README).
$fn = 40;
part = "assembly";
explode = 0;
panel_w = 164;
panel_h = 100;
panel_t = 2.6;
active_w = 154;
active_h = 87;
wall = 2.5;
body_w = panel_w + 10;
body_h = panel_h + 10;
body_depth = 40;
pi_w = 85;
pi_h = 56;
pi_t = 1.6;
pi_holes = [[-39,-24.5], [19,-24.5], [-39,24.5], [19,24.5]];
carrier_holes = [[-66,-39], [66,-39], [-66,39], [66,39]];
case_holes = [[-83,-51], [83,-51], [-83,51], [83,51]];

module rounded(w,h,r=4) {
    offset(r=r) square([w-2*r,h-2*r],center=true);
}
module slab(w,h,z,t,r=4) {
    translate([0,0,z]) linear_extrude(t) rounded(w,h,r);
}
module holes(points,z,h,d) {
    for(p=points) translate([p[0],p[1],z]) cylinder(h=h,d=d);
}
module bezel() {
    difference() {
        slab(body_w,body_h,4.6,3);
        slab(active_w,active_h,4.5,3.2,1);
        holes(case_holes,4.5,3.2,3.2);
    }
}
module enclosure() {
    difference() {
        union() {
            // Open rear shell and narrow ledge supporting the panel border.
            difference() {
                slab(body_w,body_h,-body_depth,body_depth+2);
                slab(body_w-2*wall,body_h-2*wall,-body_depth-.1,body_depth+.1,2);
                slab(panel_w-5,panel_h-5,-.1,2.2,1);
            }
            // Corner rails carry the cover and bezel screws, outside the panel.
            for(p=case_holes) translate([p[0],p[1],-body_depth]) cylinder(h=body_depth+2,d=6);
        }
        holes(case_holes,-body_depth-.1,body_depth+2.2,2.7);
        // Generic side service opening, not individual connector cutouts.
        translate([body_w/2-4,-35,-32]) cube([8,70,20]);
        // Lower cable exit and upper ventilation slots.
        translate([-16,-body_h/2-1,-26]) cube([32,5,10]);
        for(x=[-54:12:54]) translate([x,body_h/2-4,-32]) cube([5,6,20]);
    }
}
module rear_cover() {
    difference() {
        union() {
            slab(body_w,body_h,-42,2);
            holes(carrier_holes,-40,4,7);
        }
        holes(case_holes,-42.1,2.2,3.2);
        holes(carrier_holes,-42.1,6.2,2.7);
        for(x=[-54:12:54]) translate([x,-23,-42.1]) cube([5,46,2.2]);
    }
}
module carrier() {
    difference() {
        union() {
            slab(144,90,-36,3);
            holes(pi_holes,-33,4,6.5);
        }
        holes(carrier_holes,-36.1,3.2,3.2);
        holes(pi_holes,-36.1,7.2,2.7);
        for(x=[-30:12:42]) translate([x,-18,-36.1]) cube([5,36,3.2]);
        // Cable-tie slots around the uncommitted driver-board area.
        for(y=[-30,26]) translate([48,y,-36.1]) cube([12,3,3.2]);
    }
}
module oled() { slab(panel_w,panel_h,2,panel_t,1); }
module screen() { slab(active_w,active_h,4.61,.05,1); }
module pi_board() {
    difference() {
        slab(pi_w,pi_h,-29,pi_t,3);
        holes(pi_holes,-29.1,pi_t+.2,2.7);
    }
}
module ports() {
    // Approximate connector clearance boxes; not detailed component CAD.
    for(y=[-18,0,18]) translate([31,y-7,-27.4]) cube([16,14,13]);
    translate([-35,-30,-27.4]) cube([10,5,4]);
    for(x=[-18,-3]) translate([x,-30,-27.4]) cube([8,5,3]);
}
module gpio() { translate([-37,20,-27.4]) cube([51,5,8]); }
module cooler() {
    // Generic cooler envelope; verify chosen heatsink, fan and airflow.
    translate([-21,-14,-27.4]) cube([32,28,2]);
    for(x=[-20:4:10]) translate([x,-14,-25.4]) cube([1.2,28,10]);
}
module driver_board() {
    // Unknown OLED controller, clearance allowance only; retain with straps.
    translate([49,-19,-29]) cube([18,38,1.6]);
}
module assembly() {
    color("#343438") enclosure();
    color("#888780") translate([0,0,-explode*1.8]) rear_cover();
    color("#c68a32") translate([0,0,-explode*1.2]) carrier();
    color("#287c51") translate([0,0,-explode*.65]) pi_board();
    color("#b7bec3") translate([0,0,-explode*.65]) ports();
    color("#242424") translate([0,0,-explode*.65]) gpio();
    color("#8d9b9f") translate([0,0,-explode*.65]) cooler();
    color("#27526a") translate([0,0,-explode*.65]) driver_board();
    color("#262631") translate([0,0,explode*.65]) oled();
    color("#0b0b10") translate([0,0,explode*.65]) screen();
    color("#252528") translate([0,0,explode*1.3]) bezel();
}
if(part=="assembly") assembly();
else if(part=="bezel") bezel();
else if(part=="enclosure") enclosure();
else if(part=="rear_cover") rear_cover();
else if(part=="carrier") carrier();
else if(part=="oled") oled();
else if(part=="screen") screen();
else if(part=="pi_board") pi_board();
else if(part=="ports") ports();
else if(part=="gpio") gpio();
else if(part=="cooler") cooler();
else if(part=="driver_board") driver_board();
