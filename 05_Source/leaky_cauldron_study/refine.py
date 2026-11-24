import bpy, math, random, bmesh
from pathlib import Path
from mathutils import Vector
from math import pi,sin,cos,radians
R=Path(__file__).resolve().parent
base=R.parent/'leaky_cauldron_round01'
with bpy.data.libraries.load(str(base/'LeakyCauldron_Blockout.blend')) as (src,dst):
    dst.scenes=[src.scenes[0]]
s=dst.scenes[0]
s.name='The Leaky Cauldron | Hearth study'
def obj(name):
    return next(o for o in s.objects if o.name.split('.')[0]==name)
group=bpy.data.collections.new('10 | Hearth and joinery study')
s.collection.children.link(group)
def link(o,mat):
    group.objects.link(o)
    o.data.materials.append(mat)
    return o
def mesh(name,verts,faces,mat,bevel=0):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update()
    o=link(bpy.data.objects.new(name,m),mat)
    if bevel:
        mod=o.modifiers.new('Worn corners','BEVEL');mod.width=bevel;mod.segments=2
    return o
def box(name,loc,size,mat,bevel=.007):
    x,y,z=[v/2 for v in size]
    v=[(a*x,b*y,c*z) for a,b,c in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    o=mesh(name,v,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,bevel);o.location=loc;return o
def line(name,pts,rad,mat):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.bevel_depth=rad;c.bevel_resolution=2
    sp=c.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,v in zip(sp.points,pts):p.co=(*v,1)
    return link(bpy.data.objects.new(name,c),mat)
def surface(name,dark,light,rough,metal=0,frequency=10):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*light,1)
    n=m.node_tree.nodes;l=m.node_tree.links;p=next(node for node in n if node.type=='BSDF_PRINCIPLED');p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=frequency;tex.inputs['Detail'].default_value=4
    co=n.new('ShaderNodeTexCoord');l.new(co.outputs['Object'],tex.inputs[0]);r=n.new('ShaderNodeValToRGB')
    for e,v in zip(r.color_ramp.elements,[dark,light]):e.color=(*v,1)
    l.new(tex.outputs[0],r.inputs[0]);l.new(r.outputs[0],p.inputs['Base Color'])
    b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.24;b.inputs['Distance'].default_value=.008;l.new(tex.outputs[0],b.inputs['Height']);l.new(b.outputs[0],p.inputs['Normal'])
    return m
rng=random.Random(492)
iron=surface('Seasoned cast iron',(.018,.014,.013),(.14,.129,.103),.47,.62,54)
stone=surface('Smoked limestone',(.045,.038,.033),(.29,.257,.202),.86,0,16)
brick=[surface('Firebrick '+str(i),(.013,.011,.009),(.065+i*.016,.044+i*.012,.033+i*.011),.92,0,30) for i in range(4)]
paper=surface('Etching paper',(.18,.12,.066),(.56,.445,.29),.88)
ink=surface('Sienna ink',(.025,.015,.009),(.074,.044,.024),.8)
oak=obj('BAR_top').data.materials[0];brass=obj('BAR_rail').data.materials[0]
# Clear displaced blockout utensils and the square lintel in the appended scene.
for o in list(s.objects):
    if o.name.startswith(('CAULDRON','MANTEL_','FIRE_lintel','FIRE_mantel','FIRE_jamb','FIRE_flame','FIRE_core','RUG')):bpy.data.objects.remove(o,do_unlink=True)
# A shallow elliptical arch, cut into individual tapered voussoirs.
for i in range(13):
    a=.012+i*pi/13;b=(i+1)*pi/13-.012
    poly=[(1.4+ry*cos(t),1.0+rz*sin(t)) for ry,rz,t in [(.91,.34,a),(.91,.34,b),(1.23,.57,b),(1.23,.57,a)]]
    vs=[(x,y,z) for x in [5.43,5.95] for y,z in poly]
    mesh('Arch | cut limestone',vs,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],stone,.014)
for side in [-1,1]:
    for j in range(5):
        box('Stone pier',(5.69,1.4+side*1.073,.104+j*.2),(.51,.316,.194),stone,.013)
for j in range(15):
    for k in range(10):
        y=.38+k*.235+(j%2)*.117
        if y<2.44:box('Blackened brick',(5.92,y,.126+j*.09),(.07,.226,.084),rng.choice(brick),.006)
# Revolved double-wall vessel, including inner surface and rolled lip.
cx,cy=5.28,1.4
def vessel(name,cx,cy,profile,mat,n=64):
    vs=[(cx+r*cos(2*pi*i/n),cy+r*sin(2*pi*i/n),z) for r,z in profile for i in range(n)]
    fs=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(profile)-1) for i in range(n)]
    o=mesh(name,vs,fs,mat)
    for face in o.data.polygons:face.use_smooth=True
    return o
vessel('Kettle | cast double wall',cx,cy,[(.003,.34),(.19,.36),(.36,.43),(.51,.56),(.61,.74),(.63,.86),(.61,.96),(.565,1.02),(.565,1.05),(.581,1.06),(.58,1.082),(.55,1.085),(.54,1.04),(.585,.93),(.595,.81),(.56,.69),(.47,.55),(.32,.445),(.15,.405),(.003,.40)],iron)
for z in [.76,.81]:
    vessel('Cast moulding',cx,cy,[(.62,z-.014),(.637,z),(.628,z+.014)],iron)
for sign in [-1,1]:
    line('Kettle ear',[ (cx,cy+sign*(.56+.22*sin(pi*i/24)),.89+.095*sin(2*pi*i/24)+.075*i/24) for i in range(25)],.038,iron)
for i in range(3):
    a=pi+i*2*pi/3
    def foot(r,z):return (cx+r*cos(a),cy+r*sin(a),z)
    line('Tripod | splayed foot',[foot(r,z) for r,z in [(.48,.60),(.47,.49),(.52,.36),(.59,.21),(.62,.07)]],.046,iron)
    line('Tripod | forged scroll',[foot(.46+.10*cos(j*.19),.48+.096*sin(j*.19)) for j in range(28)],.024,iron)
# Hearth flagstones, fissured logs and hand-shaped flames underneath the kettle.
for i in range(3):
    for j in range(4):box('Hearth flag',(4.91+i*.40,.53+j*.57,.074),(.39,.558,.064),stone,.012)
for o in s.objects:
    if o.name.startswith('FIRE_log'):o.location.x-=.46;o.location.z+=.04;o.data.materials[0]=brick[0]
for i in range(12):
    xx=cx+rng.uniform(-.23,.23);yy=cy+rng.uniform(-.34,.34);h=rng.uniform(.09,.24)
    line('Ember | glowing split',[(xx-.07,yy,.221),(xx,yy+.01,.235),(xx+.08,yy-.012,.225)],.007,obj('FIRE_ember0').data.materials[0])
    fire=vessel('Fire tongue',xx,yy,[(.01,.21),(.038,.234),(.033,.255),(.015,.21+h*.72),(.001,.21+h)],obj('TBL_flame').data.materials[0],12)
    for vert in fire.data.vertices:vert.co.y+=.035*((vert.co.z-.21)/h)**2
# Framed original botanical ink studies in the crowded chimney gallery.
for j in range(2):
    for k in range(5):
        y=.37+k*.51+rng.uniform(-.03,.03);z=1.81+j*.52+rng.uniform(-.045,.045)
        w=rng.uniform(.39,.49);h=rng.uniform(.38,.52)
        box('Gallery | carved frame',(5.54,y,z),(.11,w,h),oak,.014)
        box('Gallery | gilt slip',(5.477,y,z),(.024,w-.052,h-.053),brass,.006)
        box('Gallery | laid paper',(5.46,y,z),(.018,w-.078,h-.079),paper,.003)
        for sprig in [-1,0,1]:
            skew=sprig*.068+rng.uniform(-.02,.02)
            def stem(t):return (5.449,y+skew*t+.012*sin(pi*t),z-.11+.22*t)
            line('Plate | ink stem',[stem(i/12) for i in range(13)],.0025,ink)
            for leaf in range(2,8):
                x0,y0,z0=stem(leaf/9);d=(-1)**leaf*.026
                line('Plate | engraved leaf',[(x0,y0,z0),(x0,y0+d,z0+.009),(x0,y0+d*1.5,z0+.028),(x0,y0+d*.36,z0+.018),(x0,y0,z0)],.002,ink)
# Directional oak grain follows each member's longest local axis.
for o in list(s.objects):
    if o.type!='MESH' or not o.data.materials:continue
    orig=o.data.materials[0]
    if not orig or not orig.name.startswith(('floor plank','oak |')):continue
    span=[max(p[i] for p in o.bound_box)-min(p[i] for p in o.bound_box) for i in range(3)]
    axis=span.index(max(span));name=orig.name+' / grain '+str(axis);m=bpy.data.materials.get(name)
    if not m:
        m=orig.copy();m.name=name;n=m.node_tree.nodes;l=m.node_tree.links
        tex=next((t for t in n if t.type=='TEX_NOISE' and t.outputs[0].is_linked and t.outputs[0].links[0].to_node.type=='VALTORGB'),None)
        if tex:
            vec=n.new('ShaderNodeVectorMath');vec.operation='MULTIPLY';sc=[24,24,24];sc[axis]=1.1;vec.inputs[1].default_value=sc
            c=n.new('ShaderNodeTexCoord');l.new(c.outputs['Object'],vec.inputs[0]);l.new(vec.outputs[0],tex.inputs[0]);tex.inputs['Scale'].default_value=2.8;tex.inputs['Distortion'].default_value=.25
    o.data.materials[0]=m
# Traditional gilt lettering, relief borders and threaded bottle closures.
sign=obj('SIGN_text');sign.data.font=bpy.data.fonts.load('/System/Library/Fonts/Supplemental/Georgia Bold.ttf');sign.data.size=.205;sign.data.materials[0]=brass
obj('SIGN_face').data.materials[0]=ink
for z in [2.195,2.565]:box('Sign | brass rule',(-2.7,2.510,z),(3.05,.007,.011),brass,.002)
for o in list(s.objects):
    if o.name.startswith('BOTTLE_') and o.name.split('_')[-1].split('.')[0].isdigit():
        idx=int(o.name.split('_')[-1].split('.')[0])
        if idx%5==1:bpy.data.objects.remove(o,do_unlink=True);continue
        if idx%3==0:
            x,y,z=o.location;q=o.scale.z
            vessel('Stoneware label',x,y,[(.051*q,z+.086*q),(.051*q,z+.17*q)],paper,16)
for name,loc,aim,power,col,size in [('Window bounce',(2.0,2.65,2.65),(-2.8,-.4,1.0),115,(.55,.70,1),2.0),('Hearth window rake',(3.2,2.9,2.48),(5.5,1.4,.83),125,(.72,.82,1),1.4)]:
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.color=col;ld.size=size;o=bpy.data.objects.new(name,ld);group.objects.link(o);o.location=loc;o.rotation_euler=(Vector(aim)-o.location).to_track_quat('-Z','Y').to_euler()
fire=obj('FIRE_light');fire.location=(5.19,1.4,.25);fire.data.energy=48;fire.data.shadow_soft_size=.19
# Project the individual period prints from the project's CC0 set photograph.
etch=bpy.data.images.load(str(base/'references'/'Leaky Cauldron set.jpg'),check_existing=True)
etch.pack()
etch['Credit']='Jack1956, Leaky Cauldron set, Wikimedia Commons, CC0. Image regions used for framed prints.'
printmat=bpy.data.materials.new('Aged engravings | set photograph')
printmat.use_nodes=True
nodes=printmat.node_tree.nodes
shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
shader.inputs['Roughness'].default_value=.93
tex=nodes.new('ShaderNodeTexImage');tex.image=etch
printmat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
# Corner order follows each photographed sheet from upper left, clockwise.
patches=[[(137,28),(263,54),(277,156),(144,145)],[(323,94),(424,119),(432,208),(325,188)],[(449,139),(507,163),(509,226),(450,208)],[(538,184),(580,199),(581,261),(539,246)],[(405,1),(460,21),(461,86),(405,64)],[(499,30),(531,48),(533,111),(500,97)],[(551,63),(584,80),(583,155),(549,139)],[(2,143),(72,147),(82,270),(2,273)]]
plates=[o for o in s.objects if o.name.startswith('Gallery | laid paper')]
for k,o in enumerate(plates):
    ix=[0,1,2,3,7,4,5,6,1,0][k]
    poly=patches[ix]
    width,height=o.dimensions.y,o.dimensions.z
    # Mesh dimensions are known directly even before the dependency graph updates.
    width=max(v.co.y for v in o.data.vertices)*2
    height=max(v.co.z for v in o.data.vertices)*2
    x,y,z=o.location
    vs=[(x-.012,y+width/2,z+height/2),(x-.012,y-width/2,z+height/2),(x-.012,y-width/2,z-height/2),(x-.012,y+width/2,z-height/2)]
    panel=mesh('Gallery | period engraving',vs,[(0,3,2,1)],printmat)
    uv=panel.data.uv_layers.new(name='Paper crop')
    for loop in panel.data.loops:
        u,v=poly[loop.vertex_index];uv.data[loop.index].uv=(u/613,1-v/850)
for o in list(s.objects):
    if o.name.startswith('Plate |'):bpy.data.objects.remove(o,do_unlink=True)
archmat=surface('Soot settled in limestone',(.014,.012,.011),(.13,.108,.086),.89,0,11)
for o in s.objects:
    if o.name.startswith(('Arch |','Stone pier')):o.data.materials[0]=archmat
    if o.name.startswith('FIRE_log'):
        o.rotation_euler.z+=rng.uniform(-.47,.47);o.location.y+=rng.uniform(-.045,.045)
for j in range(57):
    a=rng.random()*2*pi;r=rng.random()**.5
    x=cx+r*.48*cos(a);y=cy+r*.40*sin(a)
    box('Coal bed | clinker',(x,y,.13+rng.uniform(0,.015)),(.036+rng.random()*.074,.04+rng.random()*.067,.025+rng.random()*.031),rng.choice(brick),.012)
portrait_camera=bpy.data.cameras.new('Set photograph | vertical')
portrait_camera.lens=39
portrait=bpy.data.objects.new('CAM_05_SetPortrait',portrait_camera)
group.objects.link(portrait)
portrait.location=(2.55,2.67,1.53)
portrait.rotation_euler=(Vector((5.46,1.36,1.06))-portrait.location).to_track_quat('-Z','Y').to_euler()

bpy.ops.file.pack_all()
s.camera=portrait;s.cycles.device='CPU';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.resolution_x=720;s.render.resolution_y=900;s.render.resolution_percentage=100
# Write only this scene and its dependencies to the new project.
out=R/'LeakyCauldron_HearthStudy.blend'
bpy.data.libraries.write(str(out),{s},fake_user=True,compress=True)
s.render.filepath=str(R/'renders'/'SetPortrait.png');bpy.ops.render.render(scene=s.name,write_still=True)
s.render.resolution_x=1120;s.render.resolution_y=630
for cam,filename in [('CAM_02_Fireplace','Hearth'),('CAM_01_Hero','GreatRoom'),('CAM_03_Bar','Bar')]:
    s.camera=obj(cam);s.render.filepath=str(R/'renders'/(filename+'.png'));bpy.ops.render.render(scene=s.name,write_still=True)
