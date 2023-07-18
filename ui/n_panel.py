import bpy


class JSNAP_PT_Main( bpy.types.Panel):
    bl_label = "Just Snap"
    bl_space_type  =  "VIEW_3D"
    bl_region_type  =  "UI"
    bl_category = "Just Snap"

    def draw(self, context):
        layout = self.layout

        # layout.prop(pref, 'manually_set', icon='STICKY_UVS_DISABLE', text='Test')
        btn = layout.row(align=True)
        btn.scale_y = 2
        btn.operator(
            operator='jsnap.test',
            text='Just Snap Test'
        ) 
        
        layout.separator()


def register():
    bpy.utils.register_class(JSNAP_PT_Main)

def unregister():
    bpy.utils.unregister_class(JSNAP_PT_Main)