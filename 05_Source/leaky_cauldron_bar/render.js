// Buffer layout and camera convention match bake_scene.py in the first walkthrough.
const shadowSize=768;

const surfaceVertex=`#version 300 es
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
layout(location=2) in vec2 uv;
layout(location=3) in vec3 baked;
layout(location=4) in float kind;
uniform vec3 eye,right,up,forward;
uniform vec2 focal;
uniform float time;
out vec3 world,n,lighting;
out vec2 texCoord;
flat out int material;
void main(){
  world=position;
  material=int(kind+.5);
  if(material==4 && position.x>4.5 && position.z<.47){
    float w=max(0.,position.z-.20);
    world.xy+=vec2(sin(position.y*37.+time*12.),cos(position.x*35.+time*9.))*w*.22;
  }
  vec3 delta=world-eye;
  float z=dot(delta,forward);
  gl_Position=vec4(dot(delta,right)*focal.x,dot(delta,up)*focal.y,1.007*z-.18063-((material==1 || material==6 || material==7)?.000065*z:0.),z);
  n=normal; lighting=baked; texCoord=uv;
}`;

const shadowFragment=`#version 300 es
precision mediump float;
flat in int material;
void main(){if(material==4 || material==5) discard;}
`;

const surfaceFragment=`#version 300 es
precision highp float;
in vec3 world,n,lighting;
in vec2 texCoord;
flat in int material;
uniform sampler2D artwork,labels;
uniform float time;
layout(location=0) out vec4 base;
layout(location=1) out vec4 normals;
// Coarse and fine procedural detail in object scale, continuous across triangles.
float hash(vec3 p){
  p=fract(p*.3183099+vec3(.11,.27,.48))*23.;
  return fract(p.x*p.y*p.z*(p.x+p.y+p.z));
}
float noise(vec3 p){
  vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
      mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);
}
void main(){
  vec3 color=lighting;
  vec3 normal=normalize(n);
  float metal=0., rough=1., bump=0., height=.5, emissive=0.;
  if(material==9){
    vec3 ink=pow(texture(labels,texCoord).rgb,vec3(2.2));
    color*=ink*(.86+.24*noise(world*78.));
  }else if(material==8 || material==10){
    float waves=noise(world*75.);
    float mottled=noise(world*23.);
    height=waves*.35+mottled*.65;
    bool glass=material==8;
    metal=glass?1.:.4;
    rough=glass?.135+.18*mottled:.31+.22*mottled;
    color*=glass?(.63+.49*mottled):(.70+.55*height);
    bump=glass?.00029:.00070;
  }else if(material==3){
    color*=pow(texture(artwork,vec2(texCoord.x,1.-texCoord.y)).rgb,vec3(2.2))*.82;
  }else if(material==4 || material==5){
    emissive=1.;
    if(material==4){
      float flare=.46+.17*sin(time*11.+world.x*14.+world.y*17.);
      if(world.x>4.5 && world.z<.47){
        float tip=smoothstep(.22,.44,world.z);
        color=mix(vec3(2.9,1.0,.13),vec3(1.80,.31,.016),tip)*(1.+flare);
      }else color=mix(lighting,vec3(3.9,1.9,.62),flare);
    }
    if(material==5){
      float w=sin(world.z*83.)*sin(dot(world.xy,vec2(91.,91.)));
      color=vec3(1.55,1.77,2.18)*(.96+.04*w);
    }
  }else if(material==1 || material==6 || material==7){
    vec3 p=material==1?world.xyz:material==6?world.yxz:world.zxy;
    float warp=noise(p*vec3(2.8,8.,8.));
    float ribbons=noise(p*vec3(2.1,47.,47.)+vec3(0.,warp*3.,warp*4.));
    float pores=noise(p*vec3(23.,135.,135.));
    float wear=noise(world*4.6);
    height=.56*ribbons+.44*pores;
    color*=mix(.64,1.40,height)*mix(.82,1.14,wear)*vec3(1.09,.95,.81)*.85;
    bump=.0027;
  }else if(material==2){
    float hammered=noise(world*87.);
    float patina=noise(world*17.);
    height=hammered*.76+patina*.24;
    float gold=smoothstep(.015,.14,lighting.r-lighting.b);
    float brightness=dot(lighting,vec3(.22,.69,.09));
    bool iron=world.x>4.56 && abs(world.y-1.4)<.83 && world.z<1.17;
    metal=.93;
    rough=mix(mix(.57,.22,smoothstep(.12,.57,brightness)),.28,gold);
    color=color*(.54+.58*height)+(.009+.018*patina)*vec3(1.,.86,.69);
    if(iron){
      color*=.31+.28*height;
      rough=.42+.19*patina;
    }
    bump=mix(.00155,.0008,gold);
  }else{
    float plaster=noise(world*8.);
    float pits=noise(world*96.);
    height=.63*pits+.37*plaster;
    color*=.68+.43*plaster+.24*pits;
    float soot=smoothstep(4.98,5.96,world.x)*exp(-pow((world.y-1.40)*1.25,2.0))*(1.-smoothstep(1.2,2.55,world.z));
    color*=1.-.42*soot;
    if(world.x>5.38 && abs(world.y-1.4)<1.25 && world.z<1.59) color*=.63+.23*height;
    bump=.002;
  }
  vec3 dx=dFdx(world),dy=dFdy(world);
  vec3 s=cross(dy,normal),t=cross(normal,dx);
  float det=dot(dx,s);
  vec3 gradient=(dFdx(height)*s+dFdy(height)*t)*sign(det);
  normal=normalize(normal*max(abs(det),.000001)-gradient*bump);
  float nearFire=exp(-length((world-vec3(5.24,1.4,.25))*vec3(.85,1.05,1.15))*1.8);
  color+=color*.13*nearFire*sin(time*10.+world.x);
  if(emissive<.5 && world.x>4.55 && world.z<1.25){
    vec3 flame=vec3(5.23,1.4,.26)-world;
    float warm=nearFire*(.25+.75*max(0.,dot(normal,normalize(flame))))*(1.+.22*sin(time*12.));
    color+=vec3(.28,.088,.016)*warm;
  }
  if(world.x < -3.80 && abs(world.y)<2.43 && emissive<.5){
    float daylight=max(0.,dot(normal,normalize(vec3(.84,-.33,.46))));
    float shelf=(1.-smoothstep(.79,2.70,world.z))*.20;
    float lamps=0.;
    for(int i=0;i<2;i++){
      vec3 delta=vec3(-4.32,i==0?-.86:1.13,2.37)-world;
      float dist=dot(delta,delta);
      lamps+=max(0.,dot(normal,normalize(delta)))*.36/(1.+dist*1.8);
    }
    color*=.82+.34*daylight+shelf+lamps;
  }
  base=vec4(sqrt(clamp(color/4.,0.,1.)),emissive);
  normals=vec4(normal*.5+.5,metal>0.?rough*.94+.02:1.);
}`;

const fullVertex=`#version 300 es
out vec2 uv;
void main(){
  vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);
  uv=p;
  gl_Position=vec4(p*2.-1.,0.,1.);
}`;

const viewMath=`
uniform vec2 focal;
uniform sampler2D sceneDepth,geometryNormal;
float depthAt(vec2 coord){
  return .18063/max(.0001,1.007-(texture(sceneDepth,coord).r*2.-1.));
}
vec3 positionAt(vec2 coord){
  float z=depthAt(coord);
  return vec3((coord*2.-1.)*z/focal,z);
}
`;

const traceFragment=`#version 300 es
precision highp float;
in vec2 uv;
out vec4 reflection;
uniform sampler2D sceneColor;
uniform vec3 right,up,forward;
${viewMath}
vec2 toScreen(vec3 p){return p.xy*focal/max(.09,p.z)*.5+.5;}
bool outside(vec2 p){return any(lessThan(p,vec2(.003)))||any(greaterThan(p,vec2(.997)));}
void main(){
  reflection=vec4(0.);
  vec4 surface=texture(geometryNormal,uv);
  if(surface.a>.97 || texture(sceneDepth,uv).r>.9999) return;
  vec3 n=normalize(surface.xyz*2.-1.);
  vec3 viewNormal=vec3(dot(n,right),dot(n,up),dot(n,forward));
  vec3 origin=positionAt(uv);
  if(dot(viewNormal,origin)>0.)viewNormal=-viewNormal;
  vec3 ray=reflect(normalize(origin),viewNormal);
  origin+=viewNormal*.042;
  float oldT=.08;
  float oldGap=-.05;
  for(int i=0;i<27;i++){
    float a=float(i);
    float t=.16+a*.091+a*a*.0059;
    vec3 p=origin+ray*t;
    if(p.z<.10) return;
    vec2 screen=toScreen(p);
    if(outside(screen)) return;
    float gap=p.z-depthAt(screen);
    if(gap>=0. && oldGap<0.){
      float lo=oldT,hi=t;
      for(int j=0;j<5;j++){
        float mid=(lo+hi)*.5;
        vec3 q=origin+ray*mid;
        if(q.z>depthAt(toScreen(q))) hi=mid;
        else lo=mid;
      }
      vec3 hit=origin+ray*hi;
      screen=toScreen(hit);
      float error=hit.z-depthAt(screen);
      if(error<.16 && length(screen-uv)>.009){
        vec2 edge=min(screen,1.-screen);
        float weight=smoothstep(.005,.12,min(edge.x,edge.y))*exp(-hi*.10);
        reflection=vec4(texture(sceneColor,screen).rgb*weight,weight);
        return;
      }
    }
    oldGap=gap;oldT=t;
  }
}`;

const compositeFragment=`#version 300 es
precision highp float;
in vec2 uv;
out vec4 pixel;
uniform sampler2D sceneColor,reflected,shadowDepth;
uniform vec3 eye,right,up,forward;
uniform vec3 lamp,lampRight,lampUp,lampForward;
uniform vec2 reflectionPixel;
uniform int mode,showHits;
uniform float exposure,time;
${viewMath}
float occlusion(vec3 p,vec3 normal,vec3 toLight){
  vec3 from=p+normal*.014-lamp;
  float z=dot(from,lampForward);
  if(z<.09)return 1.;
  vec2 key=vec2(dot(from,lampRight),dot(from,lampUp))/z*.5+.5;
  if(any(lessThan(key,vec2(.001)))||any(greaterThan(key,vec2(.999))))return 1.;
  float depth=(1.007-.18063/z)*.5+.5;
  float bias=.0007+.0013*(1.-max(0.,dot(normal,toLight)));
  float visibility=0.;
  for(int i=-1;i<=1;i++)for(int j=-1;j<=1;j++){
    float blocker=texture(shadowDepth,key+vec2(float(i),float(j))/768.).r;
    visibility+=step(depth-bias,blocker);
  }
  return visibility/9.;
}
void main(){
  if(texture(sceneDepth,uv).r>.9999){pixel=vec4(.055,.041,.031,1.);return;}
  vec4 initial=texture(sceneColor,uv);
  vec3 lit=initial.rgb*initial.rgb*4.;
  vec4 surface=texture(geometryNormal,uv);
  vec3 p=positionAt(uv);
  vec3 world=eye+right*p.x+up*p.y+forward*p.z;
  vec3 n=normalize(surface.xyz*2.-1.);
  if(dot(n,eye-world)<0.)n=-n;
  if(initial.a<.5){
    if(surface.a<.97){
      vec3 v=normalize(eye-world), ray=reflect(-v,n);
      float fresnel=.22+.58*pow(1.-max(0.,dot(v,n)),3.);
      // Broad fallback room lighting stays valid when the reflection ray leaves the screen.
      vec3 env=mix(vec3(.055,.034,.023),vec3(.31,.38,.53),smoothstep(.2,.83,ray.z));
      env+=vec3(.40,.18,.048)*pow(max(0.,dot(ray,normalize(vec3(.7,.38,-.48)))),16.);
      if(mode>0){
        float radius=mix(.45,2.4,surface.a);
        vec2 stepSize=reflectionPixel*radius;
        vec4 reflectedColor=texture(reflected,uv)*2.;
        reflectedColor+=texture(reflected,uv+vec2(stepSize.x,0.));
        reflectedColor+=texture(reflected,uv-vec2(stepSize.x,0.));
        reflectedColor+=texture(reflected,uv+vec2(0.,stepSize.y));
        reflectedColor+=texture(reflected,uv-vec2(0.,stepSize.y));
        reflectedColor/=6.;
        vec3 hit=reflectedColor.rgb/max(.001,reflectedColor.a);
        env=mix(env,hit*hit*4.,reflectedColor.a*(1.-.41*surface.a));
      }
      lit+=fresnel*env;
    }
    if(mode==2){
      vec3 delta=lamp-world;
      float dist=length(delta);
      vec3 toLight=delta/max(.001,dist);
      float cone=smoothstep(.63,.87,dot(-toLight,lampForward));
      float diffuse=max(0.,dot(n,toLight));
      if(cone*diffuse>.009 && dist<8.){
        float visibility=occlusion(world,n,toLight);
        vec3 material=clamp(sqrt(max(lit,vec3(.006)))*1.20,.10,1.);
        float flicker=.93+.04*sin(time*3.7)+.03*sin(time*6.1);
        float energy=cone*visibility*flicker/(.67+dist*dist);
        lit+=material*vec3(1.,.67,.36)*(diffuse*energy*2.12);
        if(surface.a<.97){
          vec3 halfDirection=normalize(toLight+normalize(eye-world));
          float shine=pow(max(0.,dot(halfDirection,n)),mix(56.,10.,surface.a));
          lit+=vec3(1.,.72,.44)*(shine*energy*.38);
        }
      }
    }
  }
  vec3 exposed=lit*exposure;
  vec3 tone=exposed/(1.+exposed);
  vec3 rgb=pow(clamp(tone,0.,1.),vec3(.4545));
  if(showHits==1){
    float alpha=surface.a<.97?smoothstep(.012,.28,texture(reflected,uv).a):0.;
    rgb=mix(rgb*.46,vec3(.09,.93,.93),alpha*.92);
  }
  pixel=vec4(rgb,1.);
}
`;

function compile(gl,type,source){
  const shader=gl.createShader(type);
  gl.shaderSource(shader,source);
  gl.compileShader(shader);
  if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(shader));
  return shader;
}
function program(gl,vertex,fragment,names){
  const id=gl.createProgram();
  const vs=compile(gl,gl.VERTEX_SHADER,vertex);
  const fs=compile(gl,gl.FRAGMENT_SHADER,fragment);
  gl.attachShader(id,vs);
  gl.attachShader(id,fs);
  gl.linkProgram(id);
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  if(!gl.getProgramParameter(id,gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(id));
  return {id,u:Object.fromEntries(names.map(name=>[name,gl.getUniformLocation(id,name)]))};
}
function renderTarget(gl,width,height,colors,depth,filter){
  const fbo=gl.createFramebuffer(), textures=[];
  gl.bindFramebuffer(gl.FRAMEBUFFER,fbo);
  function allocate(format,kind,type,attachment,filtering){
    const tex=gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D,tex);
    gl.texImage2D(gl.TEXTURE_2D,0,format,width,height,0,kind,type,null);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,filtering);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,filtering);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.framebufferTexture2D(gl.FRAMEBUFFER,attachment,gl.TEXTURE_2D,tex,0);
    return tex;
  }
  for(let i=0;i<colors;i++)textures.push(allocate(gl.RGBA8,gl.RGBA,gl.UNSIGNED_BYTE,gl.COLOR_ATTACHMENT0+i,filter));
  const depthMap=depth?allocate(gl.DEPTH_COMPONENT24,gl.DEPTH_COMPONENT,gl.UNSIGNED_INT,gl.DEPTH_ATTACHMENT,gl.NEAREST):null;
  gl.drawBuffers(colors?textures.map((_,i)=>gl.COLOR_ATTACHMENT0+i):[gl.NONE]);
  if(!colors)gl.readBuffer(gl.NONE);
  if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw Error("图形缓冲区无法创建");
  gl.bindFramebuffer(gl.FRAMEBUFFER,null);
  return {fbo,textures,depth:depthMap,width,height,free(){
    for(const tex of textures)gl.deleteTexture(tex);
    if(depthMap)gl.deleteTexture(depthMap);
    gl.deleteFramebuffer(fbo);
  }};
}
function vecUnit(v){const len=Math.hypot(...v);return v.map(k=>k/len);}
function cross(a,b){return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];}
function decode64(value){
  const content=atob(value), bytes=new Uint8Array(content.length);
  for(let i=0;i<content.length;i++)bytes[i]=content.charCodeAt(i);
  return bytes;
}
async function createRenderer(canvas,data){
  const gl=canvas.getContext("webgl2",{alpha:false,antialias:false,powerPreference:"high-performance"});
  if(!gl)throw Error("请使用支持 WebGL 2 的浏览器");
  const cameraUniforms=["eye","right","up","forward","focal","time"];
  const surface=program(gl,surfaceVertex,surfaceFragment,[...cameraUniforms,"artwork","labels"]);
  const shadow=program(gl,surfaceVertex,shadowFragment,cameraUniforms);
  const trace=program(gl,fullVertex,traceFragment,["right","up","forward","focal","sceneColor","sceneDepth","geometryNormal"]);
  const combine=program(gl,fullVertex,compositeFragment,[...cameraUniforms,"sceneColor","sceneDepth","geometryNormal","reflected","shadowDepth","lamp","lampForward","lampRight","lampUp","reflectionPixel","mode","exposure","showHits"]);
  const vao=gl.createVertexArray();
  gl.bindVertexArray(vao);
  gl.bindBuffer(gl.ARRAY_BUFFER,gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER,decode64(data.vertices),gl.STATIC_DRAW);
  for(const [i,size,offset] of [[0,3,0],[1,3,12],[2,2,24],[3,3,32],[4,1,44]]){
    gl.enableVertexAttribArray(i);gl.vertexAttribPointer(i,size,gl.FLOAT,false,48,offset);
  }
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,gl.createBuffer());
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,decode64(data.indices),gl.STATIC_DRAW);
  const image=new Image();
  image.src="data:image/jpeg;base64,"+data.artwork;
  await image.decode();
  const art=gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D,art);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,image);
  gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);
  const labelImage=new Image();
  labelImage.src="data:image/png;base64,"+data.labels;
  await labelImage.decode();
  const labelTexture=gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D,labelTexture);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,labelImage);
  gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
  const shadowMap=renderTarget(gl,shadowSize,shadowSize,0,true,gl.NEAREST);
  const fullscreen=gl.createVertexArray();
  let buffers,reflection,lastLamp,lightAxes;
  function bindTexture(u,name,slot,tex){
    gl.activeTexture(gl.TEXTURE0+slot);
    gl.bindTexture(gl.TEXTURE_2D,tex);
    gl.uniform1i(u[name],slot);
  }
  function bindView(u,eye,axes,focal,time){
    gl.uniform3fv(u.eye,eye);
    gl.uniform3fv(u.right,axes.right);
    gl.uniform3fv(u.up,axes.up);
    gl.uniform3fv(u.forward,axes.forward);
    gl.uniform2fv(u.focal,focal);
    gl.uniform1f(u.time,time);
  }
  function target(map){
    gl.bindFramebuffer(gl.FRAMEBUFFER,map?.fbo??null);
    gl.viewport(0,0,map?.width??canvas.width,map?.height??canvas.height);
  }
  function geometry(){
    gl.bindVertexArray(vao);
    gl.drawElements(gl.TRIANGLES,data.triangles*3,gl.UNSIGNED_INT,0);
  }
  function fullScreen(){gl.bindVertexArray(fullscreen);gl.drawArrays(gl.TRIANGLES,0,3);}
  function feedScene(u){
    bindTexture(u,"sceneColor",0,buffers.textures[0]);
    bindTexture(u,"geometryNormal",1,buffers.textures[1]);
    bindTexture(u,"sceneDepth",2,buffers.depth);
  }
  return {
    resize(width,height){
      canvas.width=width;canvas.height=height;
      buffers?.free();reflection?.free();
      buffers=renderTarget(gl,width,height,2,true,gl.NEAREST);
      reflection=renderTarget(gl,Math.ceil(width/2),Math.ceil(height/2),1,false,gl.LINEAR);
    },
    draw({eye,axes,ratio,time,mode,lamp,aim,exposure,showHits}){
      const scale=1/Math.tan(Math.PI*31/180);
      const focal=[scale/ratio,scale];
      const lampKey=lamp.join();
      if(mode===2&&lampKey!==lastLamp){
        const forward=vecUnit(aim.map((value,i)=>value-lamp[i]));
        const right=vecUnit(cross(forward,[0,0,1]));
        lightAxes={right,up:cross(right,forward),forward};
        lastLamp=lampKey;
        target(shadowMap);
        gl.enable(gl.DEPTH_TEST);
        gl.clear(gl.DEPTH_BUFFER_BIT);
        gl.useProgram(shadow.id);
        bindView(shadow.u,lamp,lightAxes,[1,1],0);
        geometry();
      }
      target(buffers);
      gl.enable(gl.DEPTH_TEST);
      gl.clearColor(0,0,0,0);
      gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
      gl.useProgram(surface.id);
      bindView(surface.u,eye,axes,focal,time);
      bindTexture(surface.u,"artwork",0,art);
      bindTexture(surface.u,"labels",1,labelTexture);
      geometry();
      gl.disable(gl.DEPTH_TEST);
      if(mode>0){
        target(reflection);
        gl.useProgram(trace.id);
        bindView(trace.u,eye,axes,focal,time);
        feedScene(trace.u);
        fullScreen();
      }
      target(null);
      gl.useProgram(combine.id);
      const u=combine.u;
      bindView(u,eye,axes,focal,time);
      feedScene(u);
      bindTexture(u,"reflected",3,reflection.textures[0]);
      bindTexture(u,"shadowDepth",4,shadowMap.depth);
      gl.uniform2f(u.reflectionPixel,1/reflection.width,1/reflection.height);
      gl.uniform1i(u.mode,mode);
      gl.uniform1i(u.showHits,showHits&&mode>0?1:0);
      gl.uniform1f(u.exposure,exposure);
      if(mode===2){
        gl.uniform3fv(u.lamp,lamp);
        gl.uniform3fv(u.lampRight,lightAxes.right);
        gl.uniform3fv(u.lampUp,lightAxes.up);
        gl.uniform3fv(u.lampForward,lightAxes.forward);
      }
      fullScreen();
    }
  };
}
