"""Original, procedural close-up assets shared by Blender and WebGL."""
from array import array
from math import cos, hypot, pi, sin, sqrt, copysign
from random import Random

OAK = (.100,.041,.016)
DARK = (.051,.020,.009)
OILED = (.143,.069,.028)
WARM = (.181,.086,.033)
BRASS = (.280,.147,.042)
PEWTER = (.158,.172,.180)
CLAY = (.249,.158,.098)
GREEN = (.035,.082,.059)
BLACK = (.035,.037,.032)
rng = Random(4876)


class Mesh:
    def __init__(self):
        self.vertices=array('f')
        self.faces=array('I')
        self.parts=[]
        self.name=None

    def part(self,name):
        if self.name is not None:
            self.parts[-1][3]=len(self.faces)
        self.parts.append([name,len(self.vertices)//12,len(self.faces),0])
        self.name=name

    def point(self,p,n,color,mat,uv=(0,0)):
        idx=len(self.vertices)//12
        # Simple area fill for the room export. The mesh retains raw finish colors in Blender.
        self.vertices.extend((*p,*n,*uv,*color,mat))
        return idx

    def quad(self,a,b,c,d,reverse=False):
        self.faces.extend((a,d,c,a,c,b) if reverse else (a,b,c,a,c,d))

    def finish(self):
        self.parts[-1][3]=len(self.faces)
        return self


def scaled(color,factor):
    return tuple(v*factor for v in color)


def cube(mesh, at, size, radius, color, mat=1, detail=1):
    """Rounded solid with quadrant tangent normals and planar central faces."""
    half=tuple(v/2 for v in size)
    radius=min(radius,min(half)*.97)
    inner=tuple(v-radius for v in half)

    def grid(axis):
        h,k=half[axis],inner[axis]
        if detail==1:
            return [-h,-k,k,h]
        return [-h,-(h+k)*.5,-k,k,(h+k)*.5,h]

    for a,b,c in [(0,1,2),(1,2,0),(2,0,1)]:
        for sign in [-1,1]:
            patch=[]
            for u in grid(b):
                strip=[]
                for v in grid(c):
                    plane=[0.,0.,0.]
                    plane[a],plane[b],plane[c]=sign*half[a],u,v
                    nearest=[max(-k,min(k,p)) for p,k in zip(plane,inner)]
                    d=[p-q for p,q in zip(plane,nearest)]
                    l=sqrt(sum(x*x for x in d))
                    n=[x/l for x in d]
                    p=[q+x*radius+o for q,x,o in zip(nearest,n,at)]
                    fill=1+.19*n[2]+.08*n[0]
                    strip.append(mesh.point(p,n,scaled(color,fill),mat))
                patch.append(strip)
            for i in range(len(patch)-1):
                for j in range(len(patch[i])-1):
                    mesh.quad(patch[i][j],patch[i+1][j],patch[i+1][j+1],patch[i][j+1],sign<0)


def turn(mesh, at, profile, color, mat, sides=24, axis=2, power=1):
    """Lathe with closed rims and a true interior when the profile returns inward."""
    a,b=(axis+1)%3,(axis+2)%3
    points=[]
    for j,(r,h) in enumerate(profile):
        before=profile[max(0,j-1)]
        after=profile[min(len(profile)-1,j+1)]
        radial,vertical=after[1]-before[1],before[0]-after[0]
        length=hypot(radial,vertical)
        rr,zz=radial/length,vertical/length
        ring=[]
        for i in range(sides):
            angle=i*2*pi/sides
            ca,sa=cos(angle),sin(angle)
            ca,sa=copysign(abs(ca)**power,ca),copysign(abs(sa)**power,sa)
            p=list(at)
            p[a]+=r*ca;p[b]+=r*sa;p[axis]+=h
            n=[0.]*3
            n[a],n[b],n[axis]=rr*ca,rr*sa,zz
            ring.append(mesh.point(p,n,scaled(color,.89+.19*max(0.,n[2])+.10*max(0.,n[0])),mat))
        points.append(ring)
    for lo,hi in zip(points,points[1:]):
        for i in range(sides):
            j=(i+1)%sides
            mesh.quad(lo[i],lo[j],hi[j],hi[i])


def tubing(mesh, path, radius, color, mat, sides=8):
    rings=[]
    for i,p in enumerate(path):
        lo,hi=path[max(0,i-1)],path[min(i+1,len(path)-1)]
        dx,dy,dz=(b-a for a,b in zip(lo,hi))
        length=sqrt(dx*dx+dy*dy+dz*dz)
        dx,dy,dz=dx/length,dy/length,dz/length
        helper=(0,0,1) if abs(dz)<.9 else (1,0,0)
        a=(dy*helper[2],dz*helper[0]-dx*helper[2],-dy*helper[0])
        length=sqrt(sum(v*v for v in a))
        a=tuple(v/length for v in a)
        b=(dy*a[2]-dz*a[1],dz*a[0]-dx*a[2],dx*a[1]-dy*a[0])
        ring=[]
        for j in range(sides):
            t=2*pi*j/sides
            n=tuple(x*cos(t)+y*sin(t) for x,y in zip(a,b))
            ring.append(mesh.point(tuple(x+radius*y for x,y in zip(p,n)),n,color,mat))
        rings.append(ring)
    for lo,hi in zip(rings,rings[1:]):
        for i in range(sides):
            j=(i+1)%sides
            mesh.quad(lo[i],lo[j],hi[j],hi[i])


def rim_path(x, y, w, low, shoulder, rise):
    return [(x,y-w,low),(x,y-w,shoulder)]+[
        (x,y+w*cos(pi-j*pi/26),shoulder+rise*sin(j*pi/26))
        for j in range(1,26)
    ]+[(x,y+w,shoulder),(x,y+w,low),(x,y-w,low)]


def label(mesh, at, r, z0, h, style, heading, wrap=1.45, power=1):
    x,y,z=at
    columns=22
    rows=3
    colors=[(.40,.277,.122),(.44,.33,.17),(.45,.33,.20),(.33,.29,.20),
            (.30,.193,.104),(.41,.33,.23),(.38,.29,.19),(.40,.28,.15)]
    grid=[]
    for k in range(rows+1):
        ring=[]
        for i in range(columns+1):
            t=heading+(i/columns-.5)*wrap
            u=(i/columns*.91+.045)
            v=(style+(k/rows*.83+.085))/8
            ca,sa=cos(t),sin(t)
            p=(x+r*copysign(abs(ca)**power,ca),y+r*copysign(abs(sa)**power,sa),z+z0+h*k/rows)
            ring.append(mesh.point(p,(ca,sa,0),colors[style],9,(u,v)))
        grid.append(ring)
    for lo,hi in zip(grid,grid[1:]):
        for j in range(columns):
            mesh.quad(lo[j],lo[j+1],hi[j+1],hi[j])


def build_bar():
    mesh=Mesh()
    mesh.part("Counter | oak carcass and profiled top")
    cube(mesh,(-4.23,0,.515),(.60,4.66,1.02),.016,DARK,6)
    cube(mesh,(-4.23,0,.105),(.715,4.74,.134),.012,OAK,6)
    cube(mesh,(-4.20,0,.185),(.703,4.74,.046),.013,OILED,6)
    for z,depth,width,height,r,col in [
       (1.015,.661,4.718,.084,.012,DARK),(1.055,.724,4.771,.038,.013,OAK),
       (1.086,.765,4.805,.038,.013,OILED),(1.118,.825,4.851,.055,.017,OILED)]:
        cube(mesh,(-4.24,0,z),(depth,width,height),r,col,6,2)
    # A main work surface made from individual staves, with rounded outer ends.
    for i in range(4):
        cube(mesh,(-4.542+i*.199,0,1.151),(.197,4.843,.042),.011,
             scaled(OILED,(.91,1.06,1.,1.10)[i]),6,2)
    for edge in (-2.337,2.337):
        cube(mesh,(-4.234,edge,1.153),(.806,.154,.045),.012,OILED,1,2)

    mesh.part("Counter | six recessed oak panel assemblies")
    for i in range(6):
        y=-1.91+.764*i
        cube(mesh,(-3.915,y,.573),(.043,.704,.742),.016,DARK,7,2)
        cube(mesh,(-3.882,y,.577),(.046,.567,.612),.033,OAK,7,2)
        cube(mesh,(-3.860,y,.563),(.025,.470,.506),.013,scaled(OILED,.87+i*.036),7,2)
        for offset in [-.337,.337]:
            cube(mesh,(-3.883,y+offset,.578),(.071,.053,.740),.012,OAK,7)
        for z in (.216,.94):
            cube(mesh,(-3.881,y,z),(.072,.704,.049),.012,OILED,6)
        tubing(mesh,rim_path(-3.838,y,.233,.317,.652,.143),.010,WARM,6)
        tubing(mesh,rim_path(-3.844,y,.186,.354,.642,.118),.005,DARK,6)
        # Circular bosses read as hand-finished wood from the approach aisle.
        turn(mesh,(-3.837,y,.572),[(.055,0),(.055,.009),(.048,.015),(.036,.024),(.021,.030),(0,.034)],
             OILED,7,20,axis=0)
    for edge in (-2.275,2.275):
        cube(mesh,(-3.867,edge,.586),(.135,.159,.802),.021,DARK,7,2)
        turn(mesh,(-3.789,edge,.315),[(.064,0),(.063,.042),(.031,.061),(.027,.12),(.039,.22),
                 (.031,.31),(.025,.50),(.062,.568),(.063,.608)],OILED,7,24)
    mesh.part("Counter | brass footrail, saddles and finials")
    turn(mesh,(-3.715,-2.28,.257),[(0,0),(.021,0),(.032,.014),(.028,.050),(.026,.078),
         (.026,4.456),(.028,4.48),(.032,4.514),(.021,4.552),(0,4.56)],BRASS,2,24,axis=1)
    for y in (-1.84,-.69,.69,1.84):
        cube(mesh,(-3.809,y,.247),(.23,.064,.043),.016,BRASS,2,2)
        turn(mesh,(-3.718,y-.023,.257),[(.034,0),(.036,.01),(.036,.039),(.034,.047)],
             scaled(BRASS,.73),2,20,axis=1)
        for z in (.206,.293):
            turn(mesh,(-3.826,y,z),[(.017,0),(.017,.012),(.012,.018),(0,.020)],BRASS,2,12,axis=0)

    mesh.part("Back bar | shelving and moulded bays")
    cube(mesh,(-5.74,0,.482),(.45,4.84,.96),.016,DARK,6)
    cube(mesh,(-5.69,0,.967),(.52,4.89,.095),.015,OILED,6,2)
    # Six panel doors with real frames and pull knobs underneath the shelves.
    for y in (-1.98,-1.19,-.397,.397,1.19,1.98):
        cube(mesh,(-5.51,y,.52),(.056,.748,.735),.021,OAK,7)
        cube(mesh,(-5.479,y,.512),(.046,.615,.607),.015,scaled(OAK,1.26),7,2)
        turn(mesh,(-5.45,y+.23,.68),[(.016,0),(.013,.018),(.022,.033),(.016,.041),(0,.046)],BRASS,2,16,axis=0)
    for y in (-1.56,0,1.56):
        for j in range(7):
            cube(mesh,(-5.919,y+(j-3)*.209,1.817),(.065,.206,1.69),.004,
                 scaled(DARK,.66+.1*(j%4)),7)
        tubing(mesh,rim_path(-5.565,y,.675,2.368,2.515,.151),.028,OILED,6,10)
        tubing(mesh,rim_path(-5.532,y,.675,2.397,2.543,.151),.011,WARM,6)
        for z in (1.43,1.88,2.32):
            cube(mesh,(-5.704,y,z),(.439,1.48,.050),.011,OAK,6,2)
            cube(mesh,(-5.474,y,z+.003),(.048,1.48,.061),.011,OILED,6,2)
            cube(mesh,(-5.608,y,z-.036),(.116,1.457,.014),.005,WARM,6)
    for y in (-2.351,-.782,.782,2.351):
        cube(mesh,(-5.646,y,1.829),(.383,.143,1.633),.017,DARK,7,2)
        cube(mesh,(-5.446,y,1.844),(.051,.093,1.575),.014,OILED,7,2)
        for d in (-.023,0,.023):
            tubing(mesh,[(-5.415,y+d,z) for z in (1.067,1.39,2.34,2.57)],.005,DARK,7)
        for z in (1.014,2.523):
            cube(mesh,(-5.44,y,z),(.137,.205,.13),.025,OILED,7,2)
    for z,dx,h in [(2.666,.46,.070),(2.728,.51,.075),(2.784,.57,.049)]:
        cube(mesh,(-5.693,0,z),(dx,4.90,h),.020,OILED,6,2)

    variants=[
      ([(0,0),(.072,0),(.075,.012),(.074,.162),(.071,.178),(.043,.202),(.021,.228),(.019,.282),(.020,.304),(.025,.311),(.025,.322),(.014,.322),(.012,.317),(.012,.285),(0,.281)],
       (.030,.085,.054),.074,.050,.084,1,8),
      ([(0,0),(.062,.002),(.066,.014),(.065,.227),(.058,.252),(.034,.283),(.018,.32),(.017,.412),(.022,.426),(.023,.438),(.011,.438),(.011,.403),(0,.392)],
       (.084,.051,.027),.065,.080,.091,1,8),
      ([(0,0),(.074,0),(.083,.018),(.093,.065),(.092,.128),(.081,.163),(.047,.190),(.027,.212),(.028,.237),(.035,.242),(.035,.254),(.020,.255),(.017,.248),(.017,.221),(0,.21)],
       (.091,.113,.115),.093,.070,.061,1,8),
      ([(0,0),(.071,.003),(.074,.018),(.073,.148),(.071,.162),(.049,.177),(.025,.191),(.023,.235),(.025,.249),(.030,.258),(.027,.269),(.017,.270),(.016,.231),(0,.222)],
       (.098,.049,.031),.073,.046,.073,.56,8),
      ([(0,0),(.067,0),(.073,.013),(.081,.081),(.077,.171),(.061,.225),(.041,.243),(.037,.283),(.046,.291),(.046,.308),(.028,.311),(.028,.266),(0,.246)],
       (.198,.118,.064),.081,.061,.077,1,10),
    ]
    tops=(1.015,1.455,1.905,2.345)
    for bay,center in enumerate((-1.56,0,1.56)):
        for tier,z in enumerate(tops):
            if bay==1 and tier==2:
                positions=(-.55,-.41,.03,.25,.45)
            else:
                positions=(-.55,-.38,-.21,.08,.28,.44,.59)
                if (tier+bay)%2: positions=tuple(y for i,y in enumerate(positions) if i not in (1,4))
            for i,dy in enumerate(positions):
                ix=(bay*3+tier+i*2+int(rng.random()*3))%len(variants)
                mesh.part(f"Back bar | bottle {bay+1}.{tier+1}.{i+1}")
                profile,color,r,low,h,power,finish=variants[ix]
                scale=rng.uniform(.79,1.04)
                if tier==3: scale*=.78
                shift=rng.uniform(-.026,.027)
                at=(-5.741+rng.uniform(-.061,.071),center+dy+shift,z)
                shape=[(rr*scale,hh*scale) for rr,hh in profile]
                tinted=scaled(color,rng.uniform(.55,1.16))
                turn(mesh,at,shape,tinted,finish,22,power=power)
                if (i+tier)%5!=2:
                    label(mesh,at,(r+.0028)*scale,low*scale,h*scale,(5*bay+tier+i)%8,
                          rng.uniform(-.48,.48),power=power)
                rt,zt=profile[-4]
                turn(mesh,(at[0],at[1],z+(zt-.008)*scale),
                      [(rt*scale*.67,0),(rt*scale*.74,.017),(rt*scale*.63,.029),(0,.030)],
                      scaled((.145,.073,.035),rng.uniform(.76,1.1)),0,14)
                if ix==4:
                    tubing(mesh,[(at[0]+.025,at[1]+(.041+.043*sin(pi*j/18))*scale,
                                  z+(.107+.153*j/18)*scale) for j in range(19)],.010,tinted,10)

    for seq,(x,y,r,h,finish,color,angle) in enumerate([
        (-4.045,-1.82,.070,.147,2,PEWTER,.20),(-4.205,-1.28,.065,.126,10,CLAY,-.52),
        (-4.006,-.50,.075,.164,2,scaled(PEWTER,.75),.88),(-4.217,.26,.069,.115,10,GREEN,-.97),
        (-4.091,.89,.071,.151,2,scaled(BRASS,.67),-.74),(-4.221,1.58,.065,.102,10,scaled(CLAY,.76),.95),
        (-4.026,1.80,.062,.123,10,GREEN,.24)]):
        mesh.part(f"Countertop | hollow tankard {seq+1}")
        z=1.176
        profile=[(0,0),(r*.87,0),(r,.010),(r,.020),(r*.94,.029),(r*.97,h*.80),
                 (r*1.020,h*.91),(r*1.035,h*.972),(r*1.015,h),(r*.944,h),
                 (r*.906,h*.961),(r*.885,h*.914),(r*.833,h*.33),(r*.73,h*.16),(0,h*.122)]
        turn(mesh,(x,y,z),profile,color,finish,36)
        if finish==2:
            for offset in (.025,h*.76):
                turn(mesh,(x,y,z+offset),[(r*.961,0),(r*.992,.002),(r*.999,.008),(r*.962,.010)],
                     scaled(color,.56+offset*2),2,36)
        tubing(mesh,[(x+cos(angle)*(r*.93+.051*sin(pi*j/25)),
                      y+sin(angle)*(r*.93+.051*sin(pi*j/25)),z+h*(.155+j*.70/25))
                     for j in range(26)],.0105,color,finish,12)

    mesh.part("Countertop | beer taps, menu, register and loose change")
    for y,t in [(-.16,.245),(.068,.295),(.296,.252)]:
        x=-4.47
        turn(mesh,(x,y,1.18),[(0,0),(.064,0),(.064,.018),(.042,.034),(.024,.062),(.023,t-.050),
             (.031,t-.036),(.030,t-.019),(.022,t),(0,t+.004)],BRASS,2,30)
        tubing(mesh,[(x+.007+.116*j/19,y,1.18+t-.085-.042*(j/19)**3) for j in range(20)],.012,BRASS,2,12)
        turn(mesh,(x-.016,y,1.18+t-.005),[(.029,0),(.032,.013),(.027,.035),(.017,.040),(0,.046)],DARK,7,20)
    cube(mesh,(-4.30,-1.94,1.196),(.277,.287,.038),.016,DARK,6,2)
    turn(mesh,(-4.30,-1.94,1.214),[(0,0),(.103,0),(.120,.008),(.123,.025),(.118,.032),
         (.111,.031),(.100,.014),(0,.013)],scaled(BRASS,.56),2,40)
    for i in range(8):
        turn(mesh,(-4.30+rng.uniform(-.07,.07),-1.94+rng.uniform(-.065,.065),1.237+.0017*i),
             [(0,0),(.015,0),(.016,.002),(.015,.004),(0,.004)],scaled(BRASS,.74+i*.03),2,16)
    cube(mesh,(-4.286,1.166,1.233),(.302,.335,.122),.018,DARK,6,2)
    cube(mesh,(-4.286,1.166,1.300),(.321,.347,.031),.013,OILED,6,2)
    for y in (1.057,1.268):
        cube(mesh,(-4.127,y,1.245),(.018,.037,.083),.006,BRASS,2)
    flow=[(-4.081,1.166+.052*cos(pi*j/18),1.242-.020*sin(pi*j/18)) for j in range(19)]
    tubing(mesh,flow,.007,BRASS,2,10)
    # A printed paper on the counter, slanted toward the approach.
    page=[(-4.114,-.857,1.176),(-4.352,-.824,1.176),(-4.324,-.594,1.176),(-4.083,-.623,1.176)]
    pids=[mesh.point(v,(0,0,1),(.44,.34,.19),9,uv) for v,uv in zip(page,
            ((.05,(7+.09)/8),(.95,(7+.09)/8),(.95,(7+.91)/8),(.05,(7+.91)/8)))]
    mesh.quad(*pids)

    for i,y in enumerate((-1.68,-.65,.38,1.55)):
        mesh.part(f"Stool {i+1} | turned legs and recessed seat")
        x=-3.45
        turn(mesh,(x,y,.690),[(0,0),(.184,0),(.201,.009),(.207,.020),(.210,.039),(.206,.059),
             (.194,.071),(.177,.075),(.128,.071),(0,.068)],OILED,1,44)
        turn(mesh,(x,y,.695),[(.194,0),(.206,.009),(.209,.017),(.206,.022)],DARK,1,44)
        feet=[]
        for k in range(4):
            t=(k+.5)*pi/2
            a,b=x+.168*cos(t),y+.168*sin(t)
            feet.append((a,b,.28))
            turn(mesh,(a,b,.032),[(.034,0),(.029,.049),(.021,.087),(.018,.191),
                (.027,.24),(.030,.277),(.026,.31),(.017,.37),(.019,.426),(.035,.496),
                (.041,.535),(.035,.571),(.025,.607),(.028,.652)],scaled(OAK,.91+i*.09),7,18)
        for j in range(4):
            a, b=feet[j],feet[(j+1)%4]
            tubing(mesh,[a,b],.018,OILED,6,10)
    return mesh.finish()
