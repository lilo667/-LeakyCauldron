"""Render the final proposal stills from LeakyCauldron_Blockout.blend.

    blender -b LeakyCauldron_Blockout.blend --python render_views.py
"""
import bpy
import os

SC = bpy.context.scene
ROOT = os.path.dirname(bpy.data.filepath)
OUT = os.path.join(ROOT, "renders")

SC.render.engine = "CYCLES"
SC.cycles.device = "CPU"
SC.cycles.use_adaptive_sampling = True
SC.cycles.adaptive_threshold = 0.02
SC.cycles.use_denoising = True
SC.cycles.denoiser = "OPENIMAGEDENOISE"
SC.view_settings.view_transform = "AgX"
SC.view_settings.exposure = 0.9
SC.render.image_settings.file_format = "PNG"
SC.render.image_settings.color_mode = "RGB"


def shot(cam_name, path, res, samples):
    SC.camera = bpy.data.objects[cam_name]
    SC.render.resolution_x, SC.render.resolution_y = res
    SC.cycles.samples = samples
    SC.render.filepath = os.path.join(OUT, path)
    bpy.ops.render.render(write_still=True)
    print("SHOT", path)


shot("CAM_01_Hero", "01_hero_blockout.png", (1440, 810), 96)

world = SC.world
bg = world.node_tree.nodes["Background"]
old_strength = bg.inputs[1].default_value
old_color = tuple(bg.inputs[0].default_value)
old_exp = SC.view_settings.exposure
hidden = []
for o in SC.objects:
    if o.name.startswith(("CEIL", "BEAM", "CHAND", "SIGN_chain", "VOLUME")):
        if not o.hide_render:
            o.hide_render = True
            hidden.append(o)
bg.inputs[1].default_value = 2.2
bg.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
SC.view_settings.exposure = 0.0
shot("CAM_09_Plan", "04_plan_blockout.png", (1600, 1100), 64)
bg.inputs[1].default_value = old_strength
bg.inputs[0].default_value = old_color
SC.view_settings.exposure = old_exp
for o in hidden:
    o.hide_render = False
print("DONE")
