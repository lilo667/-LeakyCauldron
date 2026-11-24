"""Export a merged first-person mesh with baked direct light and shadows."""
import array
import json
import math
from functools import lru_cache
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
STATUS = ROOT / 'bake_status.json'


def material_info(mat):
    name = mat.name.lower() if mat else ''
    if name.startswith('aged engravings'):
        return (1, 1, 1), 3
    if name in ('flame', 'ember'):
        return (1.7, .47, .065), 4
    if name.startswith('glass |'):
        return (1.9, 2.05, 2.5), 5
    color = tuple(mat.diffuse_color[:3]) if mat else (.2, .15, .10)
    if mat and mat.node_tree:
        ramp = next((node for node in mat.node_tree.nodes if node.type == 'VALTORGB'), None)
        if ramp:
            color = tuple(ramp.color_ramp.evaluate(.51)[:3])
    if name.startswith('bottle glass'):
        return tuple(c*.31 for c in color), 2
    if name.startswith(('oak', 'floor plank')):
        return color, 1
    if name.startswith(('brass', 'iron', 'seasoned cast iron', 'pewter', 'bottle glass', 'mirror')):
        return color, 2
    return color, 0


def bake():
    scene = bpy.context.scene
    assert scene.name.startswith('The Leaky Cauldron')
    depsgraph = bpy.context.evaluated_depsgraph_get()
    vertices, blockers, surfaces, collision = [], [], [], []
    lights = []
    collision_names = ('BAR_body', 'STOOL_seat', 'CHAIR_seat', 'TBL_top', 'TABLE_top',
                       'BARREL', 'BENCH_seat', 'CRATE', 'Kettle | cast', 'COAT_base',
                       'Stone pier')
    for obj in scene.objects:
        name = obj.name
        if obj.type == 'LIGHT' and obj.data.energy > 0:
            point = obj.matrix_world.translation.copy()
            if obj.data.type == 'AREA' and name.startswith('WIN'):
                point += obj.matrix_world.to_quaternion() @ Vector((0, 0, -0.52))
            lights.append((point, tuple(obj.data.color), obj.data.energy, name))
        if obj.type not in {'MESH', 'CURVE', 'FONT'} or obj.hide_render:
            continue
        if name.startswith(('BAR_', 'BACKBAR', 'BOTTLE_', 'STOOL_', 'MUG_', 'TAP_', 'Stoneware label')):
            continue
        if name.startswith(('HAZE', 'VOL')) or '_daylight' in name:
            continue
        detailed = name.startswith(('Arch |','Stone pier','Gallery |','BAR_top','Hearth flag'))
        evaluated = obj.evaluated_get(depsgraph) if detailed or obj.type != 'MESH' else None
        mesh = evaluated.to_mesh() if evaluated else obj.data
        if not mesh:
            continue
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        normal_matrix = matrix.to_3x3().inverted_safe().transposed()
        if name.startswith(('FRONT_', 'BACK_', 'LEFT_', 'RIGHT_')) and 'skirt' in name:
            shift_vector = matrix.to_3x3() @ Vector((0,-.008,0))
        else:
            shift_vector = Vector((0,0,0))
        positions = [matrix @ v.co + shift_vector for v in mesh.vertices]
        if not positions:
            if evaluated:
                evaluated.to_mesh_clear()
            continue
        longest_axis = max(range(3), key=lambda axis: max(p[axis] for p in positions)-min(p[axis] for p in positions))
        shift = len(vertices)
        vertices.extend(positions)
        materials = [material_info(mat) for mat in mesh.materials]
        uv_map = mesh.uv_layers.active
        if name.startswith(collision_names) and 'band' not in name.lower():
            box = [round(fn(p[axis] for p in positions), 3) for fn in (min, max) for axis in (0, 1)]
            if box[2]-box[0] > .1 and box[3]-box[1] > .1:
                collision.append(box)
        shadow = not name.startswith(('BOTTLE_', 'Stoneware label', 'Fire tongue', 'Ember |', 'CHAND_flame'))
        for tri in mesh.loop_triangles:
            color, kind = materials[tri.material_index] if materials else ((.2,.15,.10), 0)
            if kind == 1:
                kind = (1, 6, 7)[longest_axis]
            ids = tuple(shift+i for i in tri.vertices)
            if shadow and kind not in (3, 4, 5):
                blockers.append(ids)
            normals = tuple((normal_matrix @ Vector(n)).normalized() for n in tri.split_normals)
            uvs = tuple(tuple(uv_map.uv[i].vector) for i in tri.loops) if kind == 3 and uv_map else ((0,0),)*3
            surfaces.append((ids, normals, uvs, color, kind))
        if evaluated:
            evaluated.to_mesh_clear()
    tree = BVHTree.FromPolygons(vertices, blockers, all_triangles=True)
    STATUS.write_text(json.dumps({'stage':'lighting','sourceTriangles':len(surfaces)}))
    # The stairs terminate outside the modeled ground-floor walkable area.
    collision.extend([[1.04,-4.0,5.95,-2.96],[-4.64,-2.40,-3.84,2.40],
                      *[[-3.66,y-.21,-3.24,y+.21] for y in (-1.68,-.65,.38,1.55)]] )
    sky_directions = [Vector(v).normalized() for v in [(0,0,1),(.65,.25,.4),(-.5,.68,.35),(.1,-.8,.45),(-.55,-.25,-.38)]]

    @lru_cache(maxsize=240_000)
    def irradiance(x, y, z, nx, ny, nz):
        pos = Vector((x,y,z))
        normal = Vector((nx,ny,nz)).normalized()
        origin = pos + normal*.023
        open_directions = 0
        tested = 0
        for direction in sky_directions:
            d = direction if direction.dot(normal) > 0 else -direction
            if abs(d.dot(normal)) < .10:
                continue
            tested += 1
            if tree.ray_cast(origin, d, .48)[0] is None:
                open_directions += 1
        ambient = .31 + .40 * open_directions/max(1,tested)
        result = [ambient*1.06, ambient, ambient*.89]
        for lamp, rgb, energy, light_name in lights:
            delta = lamp-origin
            distance = delta.length
            if distance < .025 or distance > 6:
                continue
            cosine = normal.dot(delta/distance)
            power = energy * (.050 if light_name.startswith('WIN') else .064)
            contribution = power * max(0, cosine) / (.60 + distance*distance)
            if contribution < .035:
                continue
            if tree.ray_cast(origin, delta/distance, max(0,distance-.055))[0] is not None:
                contribution *= .12
            for i in range(3):
                result[i] += contribution*rgb[i]
        return result

    buffer = array.array('f')
    indices = array.array('I')
    vertex_index = {}
    for ids, normals, uvs, color, kind in surfaces:
        triangle = tuple((vertices[i], n, uv) for i, n, uv in zip(ids, normals, uvs))
        stack = [(triangle, 0)]
        while stack:
            corners, depth = stack.pop()
            if depth < 8 and kind not in (3,4,5):
                lengths = [(corners[i][0]-corners[(i+1)%3][0]).length_squared for i in range(3)]
                edge = lengths.index(max(lengths))
                if lengths[edge] > .54**2 and (corners[1][0]-corners[0][0]).cross(corners[2][0]-corners[0][0]).length > .042:
                    a,b,c = [corners[(edge+i)%3] for i in range(3)]
                    middle = ((a[0]+b[0])*.5,(a[1]+b[1]).normalized(),(0,0))
                    stack.extend([((a,middle,c),depth+1),((middle,b,c),depth+1)])
                    continue
            for position, normal, uv in corners:
                numbers = tuple(round(v,4) for v in (*position,*normal))
                key = (numbers, uv, color, kind)
                index = vertex_index.get(key)
                if index is None:
                    light = irradiance(*numbers) if kind not in (4,5) else (1,1,1)
                    if kind == 2:
                        light = [value*.83+.22 for value in light]
                    rgb = [min(4, c*l) for c,l in zip(color,light)]
                    index = len(vertex_index)
                    vertex_index[key] = index
                    buffer.extend((*position, *normal, *uv, *rgb, kind))
                indices.append(index)
    (ROOT/'vertices.bin').write_bytes(buffer.tobytes())
    (ROOT/'indices.bin').write_bytes(indices.tobytes())
    stu = next(img for img in bpy.data.images if 'Leaky Cauldron set' in img.name)
    (ROOT/'engravings.jpg').write_bytes(stu.packed_file.data)
    metadata = dict(vertices=len(vertex_index), triangles=len(indices)//3, collision=collision)
    STATUS.write_text(json.dumps(metadata))


if __name__ == '__main__':
    import traceback
    try:
        bake()
    except Exception:
        STATUS.write_text(traceback.format_exc())
        raise
