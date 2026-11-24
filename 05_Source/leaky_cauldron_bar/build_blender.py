"""Assemble the model revision on a new copy of the existing Blender room."""
from pathlib import Path
import sys
from shutil import copyfile
from tempfile import TemporaryDirectory
import traceback

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from millwork import build_bar

SOURCE=ROOT.parent/'leaky_cauldron_study'/'LeakyCauldron_HearthStudy.blend'
DEST=ROOT/'LeakyCauldron_Bar.blend'
STATUS=ROOT/'blender_status.txt'


def finish(kind,label_texture):
    names={0:'Unglazed finishes',1:'Oak lengthwise grain',2:'Tarnished brass and pewter',
           6:'Oak horizontal grain',7:'Oak upright grain',8:'Colored blown glass',
           9:'Printed paper',10:'Glazed ceramics'}
    mat=bpy.data.materials.new(names[kind])
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    bsdf=next(node for node in nodes if node.type=='BSDF_PRINCIPLED')
    palette=nodes.new('ShaderNodeVertexColor')
    palette.layer_name='Finish color'
    if kind==9:
        image=nodes.new('ShaderNodeTexImage')
        image.image=label_texture
        links.new(image.outputs['Color'],bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value=.79
        return mat
    links.new(palette.outputs['Color'],bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value={0:.68,1:.42,2:.27,6:.45,7:.49,8:.18,10:.32}[kind]
    if kind==2:
        bsdf.inputs['Metallic'].default_value=.83
    if kind==8:
        bsdf.inputs['IOR'].default_value=1.46
        bsdf.inputs['Transmission Weight'].default_value=.56
    noise=nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=90 if kind not in (1,6,7) else 1
    noise.inputs['Detail'].default_value=3
    if kind in (1,6,7):
        axis={1:0,6:1,7:2}[kind]
        vector=nodes.new('ShaderNodeVectorMath')
        vector.operation='MULTIPLY'
        rate=[104.,104.,104.]
        rate[axis]=3.8
        vector.inputs[1].default_value=rate
        geometry=nodes.new('ShaderNodeNewGeometry')
        links.new(geometry.outputs['Position'],vector.inputs[0])
        links.new(vector.outputs[0],noise.inputs['Vector'])
        ramp=nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color=(.36,.27,.19,1)
        ramp.color_ramp.elements[1].color=(1.02,1.0,.92,1)
        links.new(noise.outputs['Fac'],ramp.inputs['Fac'])
        tone=nodes.new('ShaderNodeMixRGB')
        tone.blend_type='MULTIPLY'
        tone.inputs[0].default_value=.65
        links.new(palette.outputs['Color'],tone.inputs[1])
        links.new(ramp.outputs['Color'],tone.inputs[2])
        links.new(tone.outputs['Color'],bsdf.inputs['Base Color'])
    bump=nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value=.18
    bump.inputs['Distance'].default_value=.0018 if kind!=8 else .0008
    links.new(noise.outputs['Fac'],bump.inputs['Height'])
    links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    return mat


def build():
    with TemporaryDirectory(prefix='bar-model-') as folder:
        isolated=Path(folder)/SOURCE.name
        copyfile(SOURCE,isolated)
        with bpy.data.libraries.load(str(isolated)) as (src,dst):
            dst.scenes=[src.scenes[0]]
    scene=dst.scenes[0]
    scene.name='The Leaky Cauldron | Bar close-up'
    prefixes=('BAR_','BACKBAR','BOTTLE_','STOOL_','MUG_','TAP_','Stoneware label')
    obsolete=[o for o in scene.objects if o.name.startswith(prefixes)]
    for ob in obsolete:
        for collection in scene.collection.children_recursive:
            if ob.name in collection.objects:
                collection.objects.unlink(ob)
        if ob.name in scene.collection.objects:
            scene.collection.objects.unlink(ob)
    atlas=bpy.data.images.load(str(ROOT/'labels.png'),check_existing=True)
    atlas.pack()
    palette={kind:finish(kind,atlas) for kind in (0,1,2,6,7,8,9,10)}
    assets=build_bar()
    groups={key:bpy.data.collections.new(key) for key in ('Bar furniture','Bar props','Bar bottles')}
    for collection in groups.values():
        scene.collection.children.link(collection)
    for i,(name,start,first,last) in enumerate(assets.parts):
        end=assets.parts[i+1][1] if i+1<len(assets.parts) else len(assets.vertices)//12
        records=[tuple(assets.vertices[j:j+12]) for j in range(start*12,end*12,12)]
        if not records:
            continue
        tris=[tuple(v-start for v in assets.faces[j:j+3]) for j in range(first,last,3)]
        mesh=bpy.data.meshes.new(name)
        center=Vector(tuple(sum(r[k] for r in records)/len(records) for k in range(3)))
        mesh.from_pydata([Vector(rec[:3])-center for rec in records],[],tris)
        mesh.update()
        loop_uv=mesh.uv_layers.new(name='Label sheet')
        tint=mesh.color_attributes.new(name='Finish color',type='FLOAT_COLOR',domain='POINT')
        normals=[tuple(Vector(r[3:6]).normalized()) for r in records]
        kinds=tuple(sorted({int(r[11]) for r in records}))
        for kind in kinds:
            mesh.materials.append(palette[kind])
        for v,rec in zip(tint.data,records):
            v.color=(*rec[8:11],1)
        for polygon in mesh.polygons:
            polygon.use_smooth=True
            polygon.material_index=kinds.index(int(records[polygon.vertices[0]][11]))
        for loop in mesh.loops:
            u,v=records[loop.vertex_index][6:8]
            loop_uv.data[loop.index].uv=(u,1-v)
        mesh.normals_split_custom_set_from_vertices(normals)
        ob=bpy.data.objects.new(name,mesh)
        ob.location=center
        group='Bar bottles' if ' | bottle ' in name else 'Bar props' if name.startswith('Countertop') else 'Bar furniture'
        groups[group].objects.link(ob)
    def light(name,at,point,energy,size,color):
        data=bpy.data.lights.new(name,'AREA')
        data.energy=energy;data.shape='DISK';data.size=size;data.color=color
        obj=bpy.data.objects.new(name,data)
        scene.collection.objects.link(obj)
        obj.location=at
        obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()
    light('Bar | soft daylight',(-.95,-1.75,2.66),(-4.66,.36,1.30),165,2.2,(.76,.85,1.0))
    light('Bar | copper pendant bounce',(-4.08,1.07,2.35),(-5.7,.3,1.22),61,.76,(1.0,.74,.45))
    light('Bar | back shelf bounce',(-4.52,-1.46,2.49),(-5.7,-.85,1.66),42,.94,(1.0,.83,.65))
    cd=bpy.data.cameras.new('CAM | Bar hero')
    cd.lens=23.4;cd.sensor_fit='VERTICAL'
    cam=bpy.data.objects.new(cd.name,cd)
    scene.collection.objects.link(cam)
    cam.location=(-.94,-1.60,1.68)
    cam.rotation_euler=(Vector((-4.98,.19,1.51))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.camera=cam
    scene.cycles.device='CPU'
    scene.cycles.samples=32
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1440
    scene.render.resolution_y=810
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.filepath='//Bar_Cycles.png'
    bpy.data.libraries.write(str(DEST),{scene},fake_user=True,compress=True)
    STATUS.write_text(f'{len(obsolete)} old pieces replaced; {len(assets.parts)} new objects; rendering')
    scene.render.filepath=str(ROOT/'Bar_Cycles.png')
    bpy.ops.render.render(scene=scene.name,write_still=True)
    STATUS.write_text(f'{len(obsolete)} old pieces replaced; {len(assets.parts)} new objects; render complete')


try:
    build()
except Exception:
    STATUS.write_text(traceback.format_exc())
    raise
