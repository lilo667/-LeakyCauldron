"""The Leaky Cauldron - proposal-stage blockout, Blender 5.2.

Builds an editable greybox with material/lighting study for the final
project proposal (checkpoint 2026-11-30).

Run:
    blender -b --python build_leaky.py -- --render
    blender -b --python build_leaky.py -- --render --plan
"""
import bpy
import bmesh
import sys
import json
import random
from pathlib import Path
from math import radians, sin, cos, pi, atan
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
RENDERS = ROOT / "renders"
RENDERS.mkdir(exist_ok=True)

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DO_RENDER = "--render" in ARGS
DO_PLAN = "--plan" in ARGS
PREVIEW = "--preview" in ARGS
ONE = "--one" in ARGS
HEAVY = "--hero" in ARGS

random.seed(394)

# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene
SC.unit_settings.system = "METRIC"
SC.unit_settings.scale_length = 1.0

COLL = {}
CUR = None


def use_col(name):
    global CUR
    CUR = COLL[name]


for name in [
    "01_ARCHITECTURE", "02_BAR", "03_FIREPLACE", "04_STAIRS",
    "05_FURNITURE", "06_PROPS", "07_LIGHTING", "08_CAMERAS", "09_REFERENCE",
]:
    c = bpy.data.collections.new(name)
    SC.collection.children.link(c)
    COLL[name] = c


def link(ob, mat=None):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    CUR.objects.link(ob)
    if mat is not None and ob.data is not None:
        ob.data.materials.append(mat)
    return ob


# ------------------------------------------------------------------- helpers
def _bevel(ob, width):
    if width <= 0:
        return
    b = ob.modifiers.new("bevel", "BEVEL")
    b.width = width
    b.segments = 2
    b.limit_method = "ANGLE"
    b.angle_limit = radians(40)


def box(name, size, loc, mat, rot=(0, 0, 0), bevel=0.012):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = Vector(loc)
    ob.rotation_euler = rot
    link(ob, mat)
    _bevel(ob, bevel)
    return ob


def cyl(name, r, h, loc, mat, rot=(0, 0, 0), r2=None, seg=20, bevel=0.0, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=seg,
        radius1=r, radius2=(r if r2 is None else r2), depth=h,
    )
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = abs(p.normal.z) < 0.7
    ob = bpy.data.objects.new(name, me)
    ob.location = Vector(loc)
    ob.rotation_euler = rot
    link(ob, mat)
    _bevel(ob, bevel)
    return ob


def sphere(name, r, loc, mat, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=r)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    ob.location = Vector(loc)
    link(ob, mat)
    return ob


def torus(name, major, minor, loc, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major, minor_radius=minor,
        major_segments=28, minor_segments=8, location=loc, rotation=rot,
    )
    ob = bpy.context.object
    ob.name = name
    for p in ob.data.polygons:
        p.use_smooth = True
    link(ob, mat)
    return ob


def aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# ----------------------------------------------------------------- materials
def principled(m):
    return next(n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")


def new_mat(name, color, rough=0.6, metal=0.0, noise=0.0, bump=0.0,
            transmission=0.0, emission=None, emission_strength=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*color, 1.0)
    nodes = m.node_tree.nodes
    links = m.node_tree.links
    p = principled(m)
    p.inputs["Base Color"].default_value = (*color, 1.0)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if metal < 0.5:
        p.inputs["Specular IOR Level"].default_value = 0.22
    if transmission:
        p.inputs["Transmission Weight"].default_value = transmission
        p.inputs["IOR"].default_value = 1.45
    if emission is not None:
        p.inputs["Emission Color"].default_value = (*emission, 1.0)
        p.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        p.inputs["Alpha"].default_value = alpha
    if noise > 0:
        coord = nodes.new("ShaderNodeTexCoord")
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise
        tex.inputs["Detail"].default_value = 6.0
        tex.inputs["Roughness"].default_value = 0.65
        ramp = nodes.new("ShaderNodeValToRGB")
        dark = tuple(max(0.0, c * 0.55) for c in color)
        light = tuple(min(0.95, c * 1.45) for c in color)
        ramp.color_ramp.elements[0].position = 0.22
        ramp.color_ramp.elements[0].color = (*dark, 1.0)
        ramp.color_ramp.elements[1].position = 0.8
        ramp.color_ramp.elements[1].color = (*light, 1.0)
        links.new(coord.outputs["Object"], tex.inputs["Vector"])
        links.new(tex.outputs["Fac"], ramp.inputs[0])
        links.new(ramp.outputs[0], p.inputs["Base Color"])
    if bump > 0:
        coord = nodes.new("ShaderNodeTexCoord")
        fine = nodes.new("ShaderNodeTexNoise")
        fine.inputs["Scale"].default_value = 140.0
        fine.inputs["Detail"].default_value = 3.0
        bmp = nodes.new("ShaderNodeBump")
        bmp.inputs["Strength"].default_value = bump
        bmp.inputs["Distance"].default_value = 0.02
        links.new(coord.outputs["Object"], fine.inputs["Vector"])
        links.new(fine.outputs["Fac"], bmp.inputs["Height"])
        links.new(bmp.outputs[0], p.inputs["Normal"])
    return m


M = {}
M["plaster"] = new_mat("plaster | dirty limewash", (0.30, 0.25, 0.18), 0.88, noise=5.0, bump=0.35)
M["plaster_dark"] = new_mat("plaster | sooty ceiling", (0.11, 0.085, 0.06), 0.92, noise=4.0, bump=0.3)
M["oak"] = new_mat("oak | dark beams", (0.055, 0.032, 0.017), 0.62, noise=26.0, bump=0.4)
M["oak_mid"] = new_mat("oak | counter", (0.085, 0.05, 0.026), 0.55, noise=20.0, bump=0.35)
M["oak_floor"] = [new_mat("floor plank a", (0.075, 0.045, 0.024), 0.5, noise=12.0, bump=0.25),
                  new_mat("floor plank b", (0.055, 0.033, 0.018), 0.55, noise=12.0, bump=0.25),
                  new_mat("floor plank c", (0.09, 0.055, 0.03), 0.48, noise=12.0, bump=0.25)]
M["stone"] = new_mat("stone | hearth", (0.105, 0.095, 0.08), 0.9, noise=9.0, bump=0.6)
M["iron"] = new_mat("iron | blackened", (0.018, 0.018, 0.02), 0.5, metal=0.85)
M["brass"] = new_mat("brass | tarnished", (0.45, 0.28, 0.08), 0.32, metal=1.0)
M["pewter"] = new_mat("pewter", (0.30, 0.30, 0.31), 0.38, metal=1.0)
M["mirror"] = new_mat("mirror | old silvering", (0.55, 0.55, 0.52), 0.08, metal=1.0)
M["glass"] = new_mat("glass | leaded", (0.42, 0.52, 0.48), 0.08, transmission=1.0)
M["glass_green"] = new_mat("bottle glass | green", (0.02, 0.10, 0.035), 0.12, transmission=0.9)
M["glass_amber"] = new_mat("bottle glass | amber", (0.16, 0.06, 0.012), 0.12, transmission=0.9)
M["glass_clear"] = new_mat("bottle glass | clear", (0.42, 0.42, 0.40), 0.10, transmission=0.9)
M["flame"] = new_mat("flame", (1.0, 0.28, 0.03), 0.4, emission=(1.0, 0.26, 0.02), emission_strength=1.5)
M["ember"] = new_mat("ember", (1.0, 0.28, 0.04), 0.5, emission=(1.0, 0.22, 0.02), emission_strength=30.0)
M["candle"] = new_mat("candle wax", (0.62, 0.55, 0.40), 0.45)
M["window_glow"] = new_mat("window daylight card", (0.55, 0.68, 0.85), 0.5,
                           emission=(0.40, 0.56, 0.85), emission_strength=0.9)
M["volume"] = new_mat("haze | volume scatter", (0.8, 0.78, 0.72), 1.0)
_v = M["volume"].node_tree
_v.nodes.clear()
_out = _v.nodes.new("ShaderNodeOutputMaterial")
_sc = _v.nodes.new("ShaderNodeVolumeScatter")
_sc.inputs["Color"].default_value = (0.82, 0.8, 0.72, 1.0)
_sc.inputs["Density"].default_value = 0.007
_sc.inputs["Anisotropy"].default_value = 0.35
_v.links.new(_sc.outputs[0], _out.inputs["Volume"])
M["fabric"] = new_mat("rug | faded red", (0.06, 0.022, 0.017), 0.92, noise=30.0, bump=0.5)
M["paint"] = new_mat("sign paint | cream", (0.55, 0.48, 0.34), 0.7, noise=8.0, bump=0.2)

# ------------------------------------------------------------------ geometry
H = 3.05          # ceiling height
T = 0.16          # wall thickness


class Wall:
    def __init__(self, origin, angle, length):
        self.o = Vector((origin[0], origin[1], 0.0))
        self.a = angle
        self.d = Vector((cos(angle), sin(angle), 0.0))
        self.n = Vector((-sin(angle), cos(angle), 0.0))
        self.L = length

    def p(self, u, t, z):
        q = self.o + self.d * u + self.n * t
        return (q.x, q.y, z)

    def panel(self, u0, u1, z0, z1, name, mat, thick=T, t_off=0.0):
        if u1 - u0 < 1e-4 or z1 - z0 < 1e-4:
            return
        loc = self.p((u0 + u1) / 2, t_off + thick / 2, (z0 + z1) / 2)
        return box(name, (u1 - u0, thick, z1 - z0), loc, mat, rot=(0, 0, self.a), bevel=0.008)

    def build(self, openings, name, studs=True, plates=True):
        ops = sorted(openings)
        cur = 0.0
        idx = 0
        for (u0, u1, z0, z1) in ops:
            if u0 > cur + 0.01:
                self.panel(cur, u0, 0, H, f"{name}_bay{idx}", M["plaster"]); idx += 1
            if z0 > 0.02:
                self.panel(u0, u1, 0, z0, f"{name}_sill{idx}", M["plaster"]); idx += 1
            if z1 < H - 0.02:
                self.panel(u0, u1, z1, H, f"{name}_head{idx}", M["plaster"]); idx += 1
            cur = u1
        if self.L > cur + 0.01:
            self.panel(cur, self.L, 0, H, f"{name}_bay{idx}", M["plaster"])

        if plates:
            loc = self.p(self.L / 2, 0.06, H - 0.09)
            box(f"{name}_top_plate", (self.L, 0.12, 0.18), loc, M["oak"], rot=(0, 0, self.a))
            loc = self.p(self.L / 2, 0.06, 0.08)
            box(f"{name}_sole", (self.L, 0.12, 0.16), loc, M["oak"], rot=(0, 0, self.a))

        if studs:
            u = 0.55
            k = 0
            while u < self.L - 0.2:
                inside = any(u0 - 0.10 < u < u1 + 0.10 for (u0, u1, _, _) in ops)
                if not inside:
                    loc = self.p(u, 0.055, H / 2)
                    box(f"{name}_stud{k}", (0.11, 0.13, H - 0.18), loc, M["oak"],
                        rot=(0, 0, self.a), bevel=0.008)
                    k += 1
                u += 0.92
            for ue in (0.06, self.L - 0.06):
                loc = self.p(ue, 0.055, H / 2)
                box(f"{name}_corner", (0.14, 0.15, H), loc, M["oak"], rot=(0, 0, self.a))

        # skirting
        loc = self.p(self.L / 2, T - 0.03, 0.09)
        box(f"{name}_skirt", (self.L, 0.06, 0.18), loc, M["oak"], rot=(0, 0, self.a), bevel=0.008)


def window(w, u0, u1, z0, z1, tag):
    bw = 0.065
    # frame
    w.panel(u0, u0 + bw, z0, z1, f"{tag}_jambL", M["oak"], thick=0.14)
    w.panel(u1 - bw, u1, z0, z1, f"{tag}_jambR", M["oak"], thick=0.14)
    w.panel(u0, u1, z0, z0 + bw, f"{tag}_sill", M["oak"], thick=0.14)
    w.panel(u0, u1, z1 - bw, z1, f"{tag}_lintel", M["oak"], thick=0.14)
    # glass
    loc = w.p(0.5 * (u0 + u1), 0.075, 0.5 * (z0 + z1))
    box(f"{tag}_glass", (u1 - u0 - 2 * bw, 0.012, z1 - z0 - 2 * bw), loc, M["glass"],
        rot=(0, 0, w.a), bevel=0.0)
    # mullions
    n = 3
    for i in range(1, n):
        uu = u0 + bw + (u1 - u0 - 2 * bw) * i / n
        w.panel(uu - 0.022, uu + 0.022, z0 + bw, z1 - bw, f"{tag}_mull{i}", M["oak"], thick=0.09)
    zz = (z0 + z1) / 2
    w.panel(u0 + bw, u1 - bw, zz - 0.02, zz + 0.02, f"{tag}_transom", M["oak"], thick=0.09)
    # daylight card outside + area light
    loc = w.p(0.5 * (u0 + u1), T + 0.55, 0.5 * (z0 + z1))
    card = box(f"{tag}_daylight", (u1 - u0 + 1.6, 0.02, z1 - z0 + 1.6), loc, M["window_glow"],
               rot=(0, 0, w.a), bevel=0.0)
    card.visible_shadow = False
    ldata = bpy.data.lights.new(f"{tag}_area", "AREA")
    ldata.shape = "RECTANGLE"
    ldata.size = (u1 - u0) * 0.95
    ldata.size_y = (z1 - z0) * 0.95
    ldata.energy = 280.0
    ldata.color = (0.78, 0.86, 1.0)
    lo = bpy.data.objects.new(f"{tag}_area", ldata)
    lo.location = Vector(w.p(0.5 * (u0 + u1), T + 0.28, 0.5 * (z0 + z1)))
    SC.collection.objects.link(lo)
    use_col("07_LIGHTING")
    link(lo)
    aim(lo, w.p(0.5 * (u0 + u1), -1.0, 0.5 * (z0 + z1)))


def door(w, u0, u1, z1, tag, double=False):
    bw = 0.075
    w.panel(u0, u0 + bw, 0, z1, f"{tag}_jambL", M["oak"], thick=0.18)
    w.panel(u1 - bw, u1, 0, z1, f"{tag}_jambR", M["oak"], thick=0.18)
    w.panel(u0, u1, z1, z1 + 0.12, f"{tag}_head", M["oak"], thick=0.18)
    # door leaf, slightly recessed
    loc = w.p(0.5 * (u0 + u1), 0.02, (z1 - 0.05) / 2)
    box(f"{tag}_leaf", (u1 - u0 - 2 * bw - 0.02, 0.055, z1 - 0.1), loc, M["oak_mid"],
        rot=(0, 0, w.a), bevel=0.01)
    # iron straps
    for i, zz in enumerate((0.45, 1.15, 1.85)):
        loc = w.p(0.5 * (u0 + u1), -0.02, zz)
        box(f"{tag}_strap{i}", (u1 - u0 - 2 * bw - 0.12, 0.02, 0.07), loc, M["iron"],
            rot=(0, 0, w.a), bevel=0.004)
    # ring handle
    torus(f"{tag}_ring", 0.055, 0.012, w.p(u1 - bw - 0.16, -0.075, 1.12), M["brass"],
          rot=(pi / 2, 0, 0))


# floor
use_col("01_ARCHITECTURE")
box("FLOOR_sub", (12.4, 8.4, 0.04), (0, 0, -0.03), M["oak"], bevel=0.0)
for i in range(44):
    y = -3.96 + i * 0.18
    m = M["oak_floor"][i % 3]
    box(f"FLOOR_plank{i:02d}", (11.96, 0.168, 0.035), (0, y, 0.02), m, bevel=0.004)

# walls
front = Wall((-6, 4), 0.0, 12.0)
back = Wall((6, -4), pi, 12.0)
left = Wall((-6, -4), pi / 2, 8.0)
right = Wall((6, 4), -pi / 2, 8.0)

W_DOOR = (3.2, 4.4, 0.0, 2.28)
W_WIN1 = (5.6, 6.7, 1.25, 2.35)
W_WIN2 = (8.6, 9.7, 1.2, 2.3)
B_DOOR = (6.3, 7.4, 0.0, 2.2)
B_WIN = (3.0, 3.8, 1.5, 2.3)

front.build([W_DOOR, W_WIN1, W_WIN2], "FRONT")
back.build([B_DOOR, B_WIN], "BACK")
left.build([], "LEFT")
right.build([], "RIGHT")

door(front, W_DOOR[0], W_DOOR[1], W_DOOR[3], "DOOR_front")
window(front, *W_WIN1, "WIN_front_a")
window(front, *W_WIN2, "WIN_front_b")
door(back, B_DOOR[0], B_DOOR[1], B_DOOR[3], "DOOR_back")
window(back, *B_WIN, "WIN_back")

# ceiling with stair opening
use_col("01_ARCHITECTURE")
HOLE = (3.9, 5.2, -4.0, -2.7)
box("CEIL_a", (9.9, 8.0, 0.08), ((-6 + 3.9) / 2, 0, H + 0.04), M["plaster_dark"], bevel=0.0)
box("CEIL_b", (0.8, 8.0, 0.08), ((5.2 + 6) / 2, 0, H + 0.04), M["plaster_dark"], bevel=0.0)
box("CEIL_c", (1.3, 6.7, 0.08), ((3.9 + 5.2) / 2, (-2.7 + 4) / 2, H + 0.04), M["plaster_dark"], bevel=0.0)

# cross beams
for i in range(11):
    x = -5.5 + i * 1.1
    if 3.8 < x < 5.3:
        continue
    box(f"BEAM_cross{i}", (0.17, 7.96, 0.23), (x, 0, H - 0.11), M["oak"], bevel=0.012)
box("BEAM_spine", (11.9, 0.2, 0.25), (0, 0.1, H - 0.26), M["oak"], bevel=0.012)
for x in (3.93, 5.17):
    box("BEAM_hole", (0.16, 1.3, 0.22), (x, -3.35, H - 0.11), M["oak"], bevel=0.01)

# corbels against walls, quick character
for x in (-4.4, -1.8, 1.0, 3.4):
    box("CORBEL", (0.16, 0.34, 0.2), (x, 3.8, 2.62), M["oak"], rot=(radians(-18), 0, 0))

# --------------------------------------------------------------------- bar
use_col("02_BAR")
CY = 0.0
box("BAR_body", (0.62, 4.6, 1.08), (-4.24, CY, 0.54), M["oak_mid"], bevel=0.02)
box("BAR_top", (0.78, 4.76, 0.09), (-4.24, CY, 1.125), M["oak"], bevel=0.02)
# front vertical panelling
for i in range(21):
    y = -2.18 + i * 0.218
    box(f"BAR_panel{i}", (0.035, 0.07, 0.92), (-3.92, y, 0.53), M["oak"], bevel=0.006)
# brass foot rail
cyl("BAR_rail", 0.028, 4.5, (-3.83, CY, 0.26), M["brass"], rot=(pi / 2, 0, 0), seg=16)
for i in range(5):
    y = -2.1 + i * 1.05
    box("BAR_rail_bracket", (0.12, 0.05, 0.05), (-3.89, y, 0.26), M["brass"], bevel=0.004)
# back bar
box("BACKBAR_base", (0.34, 4.7, 1.0), (-5.74, CY, 0.5), M["oak_mid"], bevel=0.015)
box("BACKBAR_top", (0.4, 4.8, 0.07), (-5.74, CY, 1.02), M["oak"], bevel=0.01)
for z in (1.42, 1.86, 2.3):
    box(f"BACKBAR_shelf_{z}", (0.3, 4.5, 0.045), (-5.74, CY, z), M["oak"], bevel=0.006)
box("BACKBAR_upright_a", (0.3, 0.07, 2.6), (-5.74, -2.28, 1.3), M["oak"], bevel=0.006)
box("BACKBAR_upright_b", (0.3, 0.07, 2.6), (-5.74, 2.28, 1.3), M["oak"], bevel=0.006)
# mirror behind the shelves
box("BACKBAR_mirror", (0.02, 4.2, 1.22), (-5.93, CY, 2.0), M["mirror"], bevel=0.0)
box("BACKBAR_mirror_frame", (0.05, 4.3, 1.32), (-5.95, CY, 2.0), M["oak"], bevel=0.006)

# bottles (instanced from three meshes)
def bottle_mesh(name, mat):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.05, radius2=0.05,
                          depth=0.24, matrix=Matrix.Translation((0, 0, 0.12)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.05, radius2=0.019,
                          depth=0.075, matrix=Matrix.Translation((0, 0, 0.277)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.019, radius2=0.019,
                          depth=0.12, matrix=Matrix.Translation((0, 0, 0.375)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.024, radius2=0.024,
                          depth=0.022, matrix=Matrix.Translation((0, 0, 0.446)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me, mat


BOTTLE_ME = [bottle_mesh("bottle_green", M["glass_green"]),
             bottle_mesh("bottle_amber", M["glass_amber"]),
             bottle_mesh("bottle_clear", M["glass_clear"])]

use_col("06_PROPS")
for si, z in enumerate((1.02, 1.442, 1.882, 2.322)):
    y = -2.15
    idx = 0
    while y < 2.2:
        me, mat = BOTTLE_ME[(si + idx) % 3]
        ob = bpy.data.objects.new(f"BOTTLE_{si}_{idx}", me)
        ob.location = Vector((-5.74, y + random.uniform(-0.01, 0.01), z))
        s = random.uniform(0.85, 1.12)
        ob.scale = (s, s, s)
        ob.rotation_euler = (0, 0, random.uniform(0, 6.28))
        link(ob, mat)
        y += 0.105
        idx += 1

# taps
for i, y in enumerate((-0.5, 0.05, 0.6)):
    cyl(f"TAP_{i}", 0.024, 0.17, (-4.3, y, 1.28), M["brass"], seg=12)
    sphere(f"TAP_knob_{i}", 0.032, (-4.3, y, 1.37), M["brass"])
    cyl(f"TAP_spout_{i}", 0.013, 0.14, (-4.37, y, 1.32), M["brass"],
        rot=(0, pi / 2, 0), seg=8)

# tankards on the counter
for i in range(7):
    y = -1.7 + i * 0.52
    x = -4.15 + random.uniform(-0.04, 0.04)
    cyl(f"MUG_{i}", 0.075, 0.17, (x, y, 1.255), M["pewter"], seg=16, bevel=0.006)
    torus(f"MUG_handle_{i}", 0.045, 0.009, (x + 0.105, y, 1.25), M["pewter"],
          rot=(pi / 2, 0, 0))

# --------------------------------------------------------------- fireplace
use_col("03_FIREPLACE")
FX = 5.82
FY = 1.4
box("FIRE_breast", (0.42, 2.5, 1.5), (5.83, FY, 2.3), M["stone"], bevel=0.02)
box("FIRE_jambL", (0.42, 0.34, 1.4), (5.83, 0.42, 0.7), M["stone"], bevel=0.02)
box("FIRE_jambR", (0.42, 0.34, 1.4), (5.83, 2.38, 0.7), M["stone"], bevel=0.02)
box("FIRE_lintel", (0.44, 2.3, 0.32), (5.82, FY, 1.24), M["stone"], bevel=0.02)
box("FIRE_mantel", (0.62, 2.6, 0.12), (5.74, FY, 1.46), M["oak"], bevel=0.02)
box("FIRE_hearth", (0.72, 2.4, 0.07), (5.58, FY, 0.035), M["stone"], bevel=0.01)
box("FIRE_back", (0.06, 1.62, 1.1), (5.99, FY, 0.55), M["iron"], bevel=0.0)
box("FIRE_floor", (0.5, 1.62, 0.05), (5.72, FY, 0.06), M["iron"], bevel=0.0)
for i in range(3):
    cyl(f"FIRE_log{i}", 0.06, 0.66, (5.7, FY + (i - 1) * 0.12, 0.15 + i * 0.03),
        M["oak"], rot=(0, pi / 2, 0), seg=10)
for i in range(5):
    sphere(f"FIRE_ember{i}", 0.035, (5.65 + random.uniform(-0.06, 0.06),
                                    FY + random.uniform(-0.3, 0.3), 0.09), M["ember"])
for i in range(5):
    fy = FY + (i - 2) * 0.1
    fh = 0.16 + (i % 3) * 0.05
    fl = cyl(f"FIRE_flame{i}", 0.045, fh, (5.68, fy, 0.16 + fh / 2), M["flame"],
             r2=0.006, seg=8, smooth=False)
    fl.rotation_euler = (random.uniform(-0.12, 0.12), random.uniform(-0.12, 0.12), random.uniform(0, 6.28))
sphere("FIRE_core", 0.1, (5.68, FY, 0.16), M["ember"], scale=(1.7, 1.0, 0.55))

# cauldron by the fire
sphere("CAULDRON", 0.3, (4.85, 2.55, 0.32), M["iron"], scale=(1, 1, 0.85))
torus("CAULDRON_rim", 0.29, 0.025, (4.85, 2.55, 0.52), M["iron"], rot=(0, 0, 0))
for i in range(3):
    a = i * 2.094
    cyl(f"CAULDRON_leg{i}", 0.022, 0.16, (4.85 + 0.18 * cos(a), 2.55 + 0.18 * sin(a), 0.08),
        M["iron"], seg=8)

# rug
use_col("05_FURNITURE")
box("RUG", (1.9, 2.0, 0.014), (4.35, 1.4, 0.055), M["fabric"], bevel=0.0)

# --------------------------------------------------------------- staircase
use_col("04_STAIRS")
STEPS = 13
RISE = 0.195
RUN = 0.26
X0 = 1.05
Y0 = -3.92
W = 0.92
for i in range(STEPS):
    x0 = X0 + i * RUN
    top = (i + 1) * RISE
    box(f"STEP_{i:02d}", (RUN + 0.01, W, top), (x0 + RUN / 2, Y0 + W / 2, top / 2),
        M["oak"], bevel=0.008)
box("STAIR_landing", (1.5, W + 0.02, 0.1), (5.2, Y0 + W / 2, 2.59), M["oak"], bevel=0.01)
# balusters and handrail
ang = atan(RISE / RUN)
for i in range(STEPS):
    x = X0 + (i + 0.5) * RUN
    top = (i + 1) * RISE
    cyl(f"BALUSTER_{i:02d}", 0.022, 0.9, (x, Y0 + W - 0.03, top + 0.45), M["oak"], seg=10)
rail_len = (STEPS * RUN) / cos(ang) + 0.3
box("HANDRAIL", (rail_len, 0.07, 0.09),
    (X0 + STEPS * RUN / 2, Y0 + W - 0.03, (STEPS * RISE) / 2 + 0.95), M["oak"],
    rot=(0, -ang, 0), bevel=0.008)
box("NEWEL", (0.12, 0.12, 1.12), (X0 + 0.04, Y0 + W - 0.03, 0.56), M["oak"], bevel=0.01)
# under-stair closet door
box("STAIR_closet", (0.06, 0.86, 1.5), (X0 - 0.02, Y0 + W / 2, 0.75), M["oak_mid"], bevel=0.01)

# --------------------------------------------------------------- furniture
def chair(x, y, rot):
    c, s = cos(rot), sin(rot)

    def off(dx, dy, z):
        return (x + dx * c - dy * s, y + dx * s + dy * c, z)

    box("CHAIR_seat", (0.44, 0.42, 0.05), off(0, 0, 0.46), M["oak"], rot=(0, 0, rot), bevel=0.008)
    for dx in (-0.18, 0.18):
        for dy in (-0.17, 0.17):
            box("CHAIR_leg", (0.04, 0.04, 0.46), off(dx, dy, 0.23), M["oak"],
                rot=(0, 0, rot), bevel=0.005)
    for dx in (-0.18, 0.18):
        box("CHAIR_post", (0.045, 0.045, 0.55), off(dx, 0.17, 0.74), M["oak"],
            rot=(0, 0, rot), bevel=0.005)
    for z in (0.72, 0.86):
        box("CHAIR_slat", (0.4, 0.035, 0.07), off(0, 0.17, z), M["oak"],
            rot=(0, 0, rot), bevel=0.005)


def table(x, y, rot=0.0, r=0.46):
    cyl("TBL_top", r, 0.05, (x, y, 0.755), M["oak"], seg=28, bevel=0.008)
    cyl("TBL_pedestal", 0.06, 0.7, (x, y, 0.4), M["oak"], seg=14)
    cyl("TBL_foot", 0.24, 0.05, (x, y, 0.03), M["oak"], seg=14, bevel=0.008)
    # candle + plate
    cyl("TBL_candle", 0.022, 0.14, (x + 0.12, y - 0.05, 0.855), M["candle"], seg=10)
    sphere("TBL_flame", 0.018, (x + 0.12, y - 0.05, 0.935), M["flame"], scale=(1, 1, 2.2))
    cyl("TBL_plate", 0.13, 0.015, (x - 0.14, y + 0.08, 0.785), M["pewter"], seg=20)


for (tx, ty, tr) in ((-2.15, 1.45, 0.3), (-1.05, -2.1, -0.4), (2.55, -0.4, 1.1)):
    table(tx, ty, tr)
    for a in (0.4, 2.5, 4.6):
        chair(tx + 0.72 * cos(a + tr), ty + 0.72 * sin(a + tr), a + tr + pi / 2)

# stools at the bar
for i, y in enumerate((-1.75, -0.9, -0.05, 0.8, 1.65)):
    cyl(f"STOOL_seat{i}", 0.19, 0.07, (-3.52, y, 0.75), M["oak"], seg=18, bevel=0.01)
    for k in range(3):
        a = k * 2.094 + 0.3
        cyl(f"STOOL_leg{i}_{k}", 0.018, 0.72, (-3.52 + 0.13 * cos(a), y + 0.13 * sin(a), 0.36),
            M["oak"], seg=8)
    torus(f"STOOL_ring{i}", 0.15, 0.012, (-3.52, y, 0.28), M["iron"], rot=(0, 0, 0))

# barrels near the back door
for i, (bx, by) in enumerate(((-4.9, -3.25), (-4.25, -3.4))):
    cyl(f"BARREL{i}", 0.3, 0.86, (bx, by, 0.43), M["oak_mid"], seg=20, bevel=0.01)
    for z in (0.16, 0.5, 0.78):
        cyl(f"BARREL_band{i}_{z}", 0.305, 0.035, (bx, by, z), M["iron"], seg=20)

# books on a table
use_col("06_PROPS")
for i in range(4):
    box(f"BOOK{i}", (0.24 - i * 0.01, 0.17, 0.035), (2.45, -0.55, 0.79 + i * 0.038),
        M["fabric"], rot=(0, 0, 0.2 + i * 0.12), bevel=0.004)


# bench and rug to break up the entrance bay
box("BENCH_seat", (1.7, 0.52, 0.07), (4.35, 3.6, 0.46), M["oak_mid"], bevel=0.012)
box("BENCH_back", (1.7, 0.07, 0.52), (4.35, 3.83, 0.75), M["oak_mid"], bevel=0.012)
for bx in (3.55, 5.15):
    box("BENCH_leg", (0.07, 0.42, 0.44), (bx, 3.6, 0.22), M["oak"], bevel=0.006)
cyl("BARREL_corner", 0.3, 0.86, (5.35, 3.15, 0.43), M["oak_mid"], seg=20, bevel=0.01)
for z in (0.16, 0.5, 0.78):
    cyl(f"BARREL_corner_band{z}", 0.305, 0.035, (5.35, 3.15, z), M["iron"], seg=20)

# ------------------------------------------------------------------- sign
use_col("06_PROPS")
box("SIGN_board", (3.3, 0.05, 0.54), (-2.7, 2.55, 2.38), M["oak"], bevel=0.02)
box("SIGN_face", (3.18, 0.012, 0.44), (-2.7, 2.522, 2.38), M["paint"], bevel=0.0)

cu = bpy.data.curves.new("SIGN_text", type="FONT")
cu.body = "THE LEAKY CAULDRON"
cu.size = 0.225
cu.align_x = "CENTER"
cu.align_y = "CENTER"
cu.extrude = 0.004
txt = bpy.data.objects.new("SIGN_text", cu)
txt.location = Vector((-2.7, 2.512, 2.38))
d = Vector((0, -1, 0))
txt.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
link(txt, M["oak"])
# chains
for dx in (-1.48, 1.48):
    cyl("SIGN_chain", 0.008, 0.5, (-2.7 + dx, 2.55, 2.66), M["iron"], seg=6)


def point_light(name, loc, energy, color, radius=0.1):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    ob.location = Vector(loc)
    SC.collection.objects.link(ob)
    link(ob)
    return ob


# ---------------------------------------------------------- set dressing
use_col("06_PROPS")
M["art_a"] = new_mat("art | sepia portrait", (0.09, 0.065, 0.04), 0.75, noise=18.0, bump=0.3)
M["art_b"] = new_mat("art | dark landscape", (0.05, 0.06, 0.05), 0.75, noise=14.0, bump=0.3)
M["art_c"] = new_mat("art | faded map", (0.13, 0.10, 0.06), 0.8, noise=20.0, bump=0.3)
M["cloth"] = new_mat("cloth | dark wool", (0.035, 0.03, 0.028), 0.95, noise=30.0, bump=0.6)
M["herb"] = new_mat("dried herbs", (0.075, 0.065, 0.035), 0.9, noise=40.0, bump=0.7)


def picture(name, loc, rot, w, h, art, normal=(0, 1, 0)):
    box(name + "_frame", (w, 0.05, h), loc, M["oak"], rot=rot, bevel=0.008)
    al = (loc[0] + normal[0] * 0.042, loc[1] + normal[1] * 0.042, loc[2])
    box(name + "_art", (w - 0.09, 0.012, h - 0.09), al, art, rot=rot, bevel=0.0)


picture("PIC_right_a", (5.955, 2.95, 1.95), (0, 0, pi / 2), 0.82, 0.62, M["art_a"], (-1, 0, 0))
picture("PIC_right_b", (5.955, -0.55, 1.85), (0, 0, pi / 2), 0.6, 0.82, M["art_b"], (-1, 0, 0))
picture("PIC_right_c", (5.955, -2.15, 1.95), (0, 0, pi / 2), 0.95, 0.58, M["art_c"], (-1, 0, 0))
picture("PIC_back_a", (-3.55, -3.955, 1.9), (0, 0, 0), 0.72, 0.6, M["art_b"])
picture("PIC_back_b", (4.25, -3.955, 1.9), (0, 0, 0), 0.85, 0.62, M["art_a"])

# coat rack by the door
cyl("COAT_pole", 0.028, 1.85, (-5.15, 3.4, 0.93), M["oak"], seg=10)
cyl("COAT_base", 0.24, 0.05, (-5.15, 3.4, 0.03), M["oak"], seg=16, bevel=0.01)
for k in range(3):
    a = k * 2.094
    box("COAT_hook", (0.16, 0.03, 0.03), (-5.15 + 0.08 * cos(a), 3.4 + 0.08 * sin(a), 1.62),
        M["iron"], rot=(0, 0, a), bevel=0.004)
cyl("COAT_cloak", 0.2, 0.95, (-5.15, 3.4, 1.12), M["cloth"], r2=0.1, seg=14, smooth=False)

# hanging herb bundles from the beams
for hx, hy in ((-5.0, 0.4), (-3.4, -1.5), (0.4, 1.4), (3.0, -1.0), (1.9, 2.2)):
    cyl("HERB", 0.1, 0.38, (hx, hy, 2.6), M["herb"], r2=0.035, seg=10, smooth=False)
    cyl("HERB_string", 0.006, 0.22, (hx, hy, 2.88), M["iron"], seg=5)

# crates near the back wall
for i, (cx, cy, cz, s) in enumerate(((-5.25, -3.35, 0.26, 0.5), (-5.2, -2.75, 0.22, 0.42))):
    box(f"CRATE{i}", (s, s, s), (cx, cy, cz), M["oak_mid"], rot=(0, 0, 0.2 * i), bevel=0.01)

# mantel candles
for i, my in enumerate((0.75, 2.05)):
    cyl(f"MANTEL_candle{i}", 0.025, 0.18, (5.72, my, 1.61), M["candle"], seg=10)
    sphere(f"MANTEL_flame{i}", 0.017, (5.72, my, 1.72), M["flame"], scale=(1, 1, 2.0))

# pendants over the bar
for i, py in enumerate((-0.9, 1.25)):
    cyl(f"PENDANT_cord{i}", 0.006, 0.55, (-4.05, py, 2.72), M["iron"], seg=5)
    cyl(f"PENDANT_shade{i}", 0.19, 0.14, (-4.05, py, 2.4), M["iron"], r2=0.05, seg=18, bevel=0.004)
    sphere(f"PENDANT_bulb{i}", 0.035, (-4.05, py, 2.36), M["flame"], scale=(1, 1, 1.2))
    point_light(f"PENDANT_light{i}", (-4.05, py, 2.3), 22.0, (1.0, 0.66, 0.34), 0.12)

# ----------------------------------------------------------------- lights
use_col("07_LIGHTING")


def chandelier(x, y, z=2.42):
    cyl("CHAND_chain", 0.01, 0.62, (x, y, z + 0.33), M["iron"], seg=6)
    torus("CHAND_ring", 0.4, 0.022, (x, y, z), M["iron"])
    for k in range(6):
        a = k * pi / 3
        cx, cy = x + 0.34 * cos(a), y + 0.34 * sin(a)
        cyl("CHAND_candle", 0.02, 0.14, (cx, cy, z + 0.1), M["candle"], seg=8)
        sphere("CHAND_flame", 0.016, (cx, cy, z + 0.19), M["flame"], scale=(1, 1, 2.0))
    point_light("CHAND_light", (x, y, z + 0.12), 70.0, (1.0, 0.62, 0.3), 0.3)


chandelier(-2.6, 1.2)
chandelier(1.5, -1.1)
chandelier(-1.0, -2.9)

# fire light
point_light("FIRE_light", (5.58, FY, 0.55), 150.0, (1.0, 0.40, 0.10), 0.35)
# sconces by the front door
for i, x in enumerate((-4.0, 2.0)):
    box(f"SCONCE_plate{i}", (0.13, 0.035, 0.34), (x, 3.945, 2.0), M["iron"], bevel=0.006)
    cyl(f"SCONCE_arm{i}", 0.02, 0.22, (x, 3.86, 2.0), M["iron"], rot=(radians(90), 0, 0), seg=8)
    cyl(f"SCONCE_pan{i}", 0.06, 0.018, (x, 3.78, 2.035), M["iron"], seg=12)
    cyl(f"SCONCE_candle{i}", 0.025, 0.16, (x, 3.78, 2.12), M["candle"], seg=8)
    sphere(f"SCONCE_flame{i}", 0.018, (x, 3.78, 2.22), M["flame"], scale=(1, 1, 2.0))
    point_light(f"SCONCE_light{i}", (x, 3.7, 2.2), 9.0, (1.0, 0.55, 0.25), 0.05)

# candle lights on the three tables
for (tx, ty, tr) in ((-2.15, 1.45, 0.3), (-1.05, -2.1, -0.4), (2.55, -0.4, 1.1)):
    point_light("TABLE_candle", (tx + 0.12, ty - 0.05, 0.95), 3.0, (1.0, 0.55, 0.25), 0.04)

# world
world = bpy.data.worlds.new("World")
SC.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.012, 0.016, 0.026, 1.0)
bg.inputs[1].default_value = 0.55

# soft ceiling fill to fake bounce light
_fd = bpy.data.lights.new("FILL_ceiling", "AREA")
_fd.shape = "RECTANGLE"
_fd.size = 5.5
_fd.size_y = 3.5
_fd.energy = 0.0
_fd.color = (1.0, 0.86, 0.72)
_fo = bpy.data.objects.new("FILL_ceiling", _fd)
_fo.location = Vector((0.2, 0.2, 2.15))
SC.collection.objects.link(_fo)
link(_fo)
aim(_fo, (0.2, 0.2, 0.0))

# interior haze volume
box("VOLUME_room", (11.82, 7.82, 2.9), (0, 0, 1.47), M["volume"], bevel=0.0)

# ----------------------------------------------------------------- cameras
use_col("08_CAMERAS")


def camera(name, loc, target, lens=24.0, ortho=None, sensor=36.0):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = sensor
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cd)
    ob.location = Vector(loc)
    SC.collection.objects.link(ob)
    link(ob)
    aim(ob, target)
    return ob


CAM_HERO = camera("CAM_01_Hero", (2.4, -2.5, 1.55), (-2.7, 2.0, 1.42), 22.0)
CAM_FIRE = camera("CAM_02_Fireplace", (2.05, 0.85, 1.58), (5.9, 1.4, 1.12), 24.0)
CAM_BAR = camera("CAM_03_Bar", (-1.95, 2.55, 1.52), (-4.9, -0.5, 1.02), 30.0)
CAM_REV = camera("CAM_04_Reverse", (1.9, 2.9, 1.6), (1.2, -2.6, 1.3), 24.0)
CAM_PLAN = camera("CAM_09_Plan", (0, 0, 12), (0, 0, 0), ortho=13.4)

SC.camera = CAM_HERO

# ------------------------------------------------------------------ render
SC.render.engine = "CYCLES"
SC.cycles.device = "CPU"
SC.cycles.samples = 24 if PREVIEW else 64
SC.cycles.use_adaptive_sampling = True
SC.cycles.adaptive_threshold = 0.02
SC.cycles.use_denoising = True
SC.cycles.denoiser = "OPENIMAGEDENOISE"
SC.cycles.max_bounces = 6
SC.cycles.diffuse_bounces = 3
SC.cycles.glossy_bounces = 3
SC.cycles.transmission_bounces = 4
SC.cycles.transparent_max_bounces = 4
SC.render.use_persistent_data = True
SC.render.film_transparent = False
SC.render.image_settings.file_format = "PNG"
SC.render.image_settings.color_mode = "RGB"
SC.render.resolution_percentage = 100
SC.view_settings.view_transform = "AgX"
try:
    SC.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
SC.view_settings.exposure = 0.9


# subtle bloom so candle/fire highlights roll off instead of clipping
try:
    SC.use_nodes = True
    nt = SC.node_tree
    nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers")
    gl = nt.nodes.new("CompositorNodeGlare")
    gl.inputs["Type"].default_value = "Fog Glow"
    gl.inputs["Quality"].default_value = "High"
    gl.inputs["Threshold"].default_value = 1.15
    gl.inputs["Strength"].default_value = 0.55
    gl.inputs["Size"].default_value = 0.55
    cp = nt.nodes.new("CompositorNodeComposite")
    nt.links.new(rl.outputs["Image"], gl.inputs["Image"])
    nt.links.new(gl.outputs["Image"], cp.inputs["Image"])
except Exception as e:
    print("COMPOSITOR_SKIP", e)

# quick sanity stats
objects = [o for o in SC.objects if o.type == "MESH"]
tris = 0
for o in objects:
    tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
stats = {
    "objects": len(SC.objects),
    "meshes": len(objects),
    "materials": len(bpy.data.materials),
    "tris_base": tris,
    "cameras": [o.name for o in SC.objects if o.type == "CAMERA"],
}
(ROOT / "scene_stats.json").write_text(json.dumps(stats, indent=2))
print("STATS", json.dumps(stats))

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "LeakyCauldron_Blockout.blend"))


def render(cam, out, res, samples):
    SC.camera = cam
    SC.render.resolution_x, SC.render.resolution_y = res
    SC.cycles.samples = samples
    SC.render.filepath = str(RENDERS / out)
    bpy.ops.render.render(write_still=True)
    print("RENDERED", out)


if DO_RENDER:
    if ONE:
        render(CAM_HERO, "00_hero_test.png", (960, 540), 32)
    if HEAVY:
        render(CAM_HERO, "01_hero_blockout.png", (1440, 810), 96)
    else:
        render(CAM_HERO, "01_hero_blockout.png", (1440, 810), 96)
    if not ONE:
        render(CAM_FIRE, "02_fireplace_blockout.png", (1200, 675), 72)
        render(CAM_BAR, "03_bar_blockout.png", (1200, 675), 72)

if DO_PLAN:
    # ceiling and hanging fixtures hidden for the plan
    hidden = []
    for o in SC.objects:
        if o.name.startswith(("CEIL", "BEAM", "CHAND", "SIGN_chain", "VOLUME")):
            if not o.hide_render:
                o.hide_render = True
                hidden.append(o)
    _old_exp = SC.view_settings.exposure
    bg.inputs[1].default_value = 2.2
    bg.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
    SC.view_settings.exposure = 0.0
    render(CAM_PLAN, "04_plan_blockout.png", (1600, 1100), 64)
    bg.inputs[1].default_value = 0.35
    bg.inputs[0].default_value = (0.012, 0.016, 0.026, 1.0)
    SC.view_settings.exposure = 0.9
    for o in hidden:
        o.hide_render = False
    SC.camera = CAM_HERO
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "LeakyCauldron_Blockout.blend"))
