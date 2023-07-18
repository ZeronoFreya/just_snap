import bpy
import gpu
import time
import threading
from gpu_extras.batch import batch_for_shader

bl_info = {
    "name": "Just Snap",
    "category": "zeronofreya",
    "author": "zeronofreya",
    "blender": (3, 0, 0),
    "location": "N面板",
    "description": "",
    "wiki_url": "",
    "tracker_url": "",
    "version": ('0', '0', '1'),
}

from . import ui
from .just_snap import JustSnap

classes = (
    ui,
)

shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')


def draw(self, ctx):
    
    gpu.state.blend_set("ALPHA")
    # gpu.state.depth_test_set("LESS")
    gpu.state.point_size_set(10)
    # print(self.coords)
    batch = batch_for_shader(shader, 'POINTS', {"pos": self.coords})
    shader.bind()
    shader.uniform_float("color", (0.8, 0, 0, 1.0))
    batch.draw(shader)
    gpu.state.point_size_set(5)

class JSNAP_OT_test(bpy.types.Operator):
    bl_idname = "jsnap.test"
    bl_label = ""
    bl_description=""
    bl_options = {'REGISTER', 'UNDO'}

    def mousemove(self):
        isSnaped, location, obj_name, closest = self.jsnap.get_snap_point(self.ctx, self.evt)
        if isSnaped:
            self.ctx.scene.cursor.location = location
            self.coords = [location]
        else:
            self.coords = closest
        self.area.tag_redraw()

    def execute(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self.test_handler, 'WINDOW')
        self.area.tag_redraw()
        self.jsnap.exit()
        return {'FINISHED'} 

    def invoke(self, context, event):
        # self.execute(context)
        self.ctx = context
        self.evt = event
        self.__kd_debounced = None
        self.area = context.area
        self.coords = []
        args = (self, context)
        self.test_handler = bpy.types.SpaceView3D.draw_handler_add(draw, args, 'WINDOW', 'POST_VIEW')
        self.jsnap = JustSnap(context)
        # 进入running modal状态
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        event_type = event.type
        if event_type == 'ONE' and event.value == 'PRESS':
            self.jsnap.snap_type = "POINTS"
        elif event_type == 'TWO' and event.value == 'PRESS':
            self.jsnap.snap_type = "MIDPOINTS"
        elif event_type == 'THREE' and event.value == 'PRESS':
            self.jsnap.snap_type = "FACES"
        elif event_type == 'O' and event.value == 'PRESS':
            self.jsnap.snap_type = "ORIGINS"
        elif event_type == 'MOUSEMOVE':
            # print("move")
            # self.mousemove()
            self.evt = event
            if self.__kd_debounced is not None:
                self.__kd_debounced.cancel()
            self.__kd_debounced = threading.Timer(0.01, self.mousemove)
            self.__kd_debounced.start()
            
        elif event_type in {'LEFTMOUSE', 'ESC'}:                                
            return self.execute(context)
        elif event_type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            print("zoom")
            return {'PASS_THROUGH'}
        elif event_type == 'MIDDLEMOUSE' and event.value == 'PRESS':
            print("rotate")
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}
        

def register():
    bpy.utils.register_class(JSNAP_OT_test)
    for cls in classes:
        try:
            cls.register()
        except Exception as e:
            print(e)

def unregister():
    bpy.utils.unregister_class(JSNAP_OT_test)
    for cls in classes:
        try:
            cls.unregister()
        except Exception as e:
            print(e)

if __name__ == "__main__":
    register()