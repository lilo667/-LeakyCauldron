"""Package the bar revision as a standalone offline walkthrough."""
from array import array
from base64 import b64encode
import json
from pathlib import Path

from millwork import build_bar

ROOT = Path(__file__).resolve().parent


def encode(data):
    return b64encode(data).decode('ascii')


scene = json.loads((ROOT/'bake_status.json').read_text())
room = (ROOT/'vertices.bin').read_bytes()
room_indices = (ROOT/'indices.bin').read_bytes()
assert len(room) == scene['vertices']*48
assert len(room_indices) == scene['triangles']*12
bar = build_bar()
old_vertices = scene['vertices']
index_buffer = array('I',(v+old_vertices for v in bar.faces))
scene.update(
    vertices=encode(room+bar.vertices.tobytes()),
    indices=encode(room_indices+index_buffer.tobytes()),
    triangles=scene['triangles']+len(bar.faces)//3,
    artwork=encode((ROOT/'engravings.jpg').read_bytes()),
    labels=encode((ROOT/'labels.png').read_bytes()),
)
template = (ROOT/'player.html').read_text()
assert template.count('<!-- SCENE -->')==1 and template.count('<!-- RENDER -->')==1
template=template.replace('<!-- SCENE -->','<script>const GEOMETRY='+json.dumps(scene,separators=(',',':'))+';</script>')
template=template.replace('<!-- RENDER -->','<script>\n'+(ROOT/'render.js').read_text()+'</script>')
(ROOT/'LeakyCauldron_Bar.html').write_text(template)
print(scene['triangles'], 'triangles')
