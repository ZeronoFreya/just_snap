import bpy
import bmesh
from math import floor
from mathutils import Vector, kdtree, bvhtree
from . import just_utils

import gpu
from gpu_extras.batch import batch_for_shader

shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')

def draw(self, ctx):

    if self.xxxx is None:
        return
    coords = list(self.xxxx.keys())

    
    gpu.state.blend_set("ALPHA")
    # gpu.state.depth_test_set("LESS")
    gpu.state.point_size_set(10)
    # print(self.coords)
    batch = batch_for_shader(shader, 'POINTS', {"pos": coords})
    shader.bind()
    shader.uniform_float("color", (0.0, 1.0, 0.0, 1.0))
    batch.draw(shader)
    gpu.state.point_size_set(5)

class JustSnap:
    # 局部视图下:
    # 由于API bug问题，无法获取局部视图内的物体，ray_cast会碰撞到局部视图之外的物体，
    # 当判断为局部视图时，会隐藏外部物体，并储存物体名到 
    # bpy.context.scene["just_snap_hide_obj"]
    # 以便在脚本崩溃时恢复物体显示
    # 退出时一定要调用exit方法，否则被隐藏的物体不会被显示
    def __init__(self, context):
        if context.area is None or context.area.type != 'VIEW_3D': 
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return 
        region = None
        for region_item in context.area.regions:
            if region_item.type == 'WINDOW':
                region = region_item
        if not region:
            return 
        # print("JustSnap")
        self.__ctx = context
        self.__area = context.area
        self.__region = region
        self.__space_data = context.space_data
        self.__rv3d = context.space_data.region_3d
        self.__local_view = context.space_data.local_view

        # all_objs = [obj for obj in bpy.data.objects if obj.visible_get()]
        # # all_scene_objects = [obj for obj in context.view_layer.objects if not obj.hide_get()]
        # print(all_objs)
        # self.__visible_objs = just_utils.get_visible_objs(
        #         self.__ctx, self.__local_view)

        # 获取可见对象，
        # 局部模式，在插件中正常，但在编辑器中却获得全部物体，大概是context的原因？
        # 不知道可不可靠
        self.__visible_objs = [obj for obj in context.scene.objects if obj.visible_get()]

        self.__visible_objs_name = [obj.name for obj in self.__visible_objs]
        print(self.__visible_objs_name)
        context.scene["just_snap_hide_obj"] = self.__visible_objs_name
        self.__not_in_local = None
        if self.__local_view:
            # ray_cast 会碰撞到所有显示物体，包括局部视图外及场景外(以某个物体的实例显示的情况)
            # 所以隐藏掉，不清楚是不是bug
            all_not_local_objs = [obj for obj in context.scene.objects if obj.name not in self.__visible_objs_name]
            # print(all_objs)
            self.__not_in_local = [obj for obj in all_not_local_objs if not obj.hide_get()]
            for obj in self.__not_in_local:
                obj.hide_set(True)

        self.__snap_type_list = ["ORIGINS", "POINTS", "MIDPOINTS", "FACES"]
        self.__snap_type = "ORIGINS"
        
        self.__objs_data = {
            "box": {},
            "data":{}
        }
        # self.__bound_box = {}
        # self.__bmesh = {}
        # self.__get_objs_bound_box()  
        for obj in self.__visible_objs:
            size = obj.dimensions.length 
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            # bm = bmesh.from_edit_mesh(me)
            matrix = obj.matrix_world
            bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
            # print([(v.index, v.co) for v in bm.verts])
            self.__objs_data["box"][obj.name] = [matrix @ Vector(loc) for loc in obj.bound_box]
            self.__objs_data["data"][obj.name] = {
                "name": obj.name,
                "size": size,
                "location": obj.location,
                "matrix_w": matrix,
                "matrix_l": obj.matrix_local,
                "bm": bm,
                "bvh": bvhtree.BVHTree.FromBMesh(bm)
            }
            # self.__bmesh[obj.name] = bm
            # self.__bound_box[obj.name] = [matrix @ Vector(loc) for loc in obj.bound_box] 

        

        self.__reset_data()

        self.xxxx = None
        args = (self, context)
        self.test_handler = bpy.types.SpaceView3D.draw_handler_add(draw, args, 'WINDOW', 'POST_PIXEL')
    
    def exit(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.test_handler, 'WINDOW')
        
        if self.__not_in_local is not None:
            for obj in self.__not_in_local:
                obj.hide_set(False)
        
        for data in self.__objs_data["data"].values():
            data["bvh"] = None
            data["bm"].free()

    @property
    def snap_type(self):
        return self.__snap_type

    # @property
    # def xray_mode(self):
    #     return self.__xray_mode

    @snap_type.setter
    def snap_type(self, snap_type):
        if snap_type in self.__snap_type_list:
            self.__snap_type = snap_type
            # print(snap_type)

    # @snap_type.setter
    # def xray_mode(self, xray_mode):
    #     if snap_type in self.__snap_type_list:
    #         self.__snap_type = snap_type

    def __get_objs_under_mouse(self):
        x, y = self.mouse_position
        objs = []
        for obj_name, obj_area in self.__screen_bound_data.items():  
            min_v = obj_area[0]
            max_v = obj_area[1]
            if x > min_v[0] and x < max_v[0] and \
                    y > min_v[1] and y < max_v[1]:
                objs.append(obj_name)
        return objs

    # def __get_objs_bound_box(self):
    #     for obj in self.__visible_objs:
    #         matrix = obj.matrix_world
    #         self.__bound_box[obj.name] = [matrix @ Vector(loc) for loc in obj.bound_box]
    
    def __update_mouse(self, event):
        self.mouse_position = (event.mouse_region_x, event.mouse_region_y)
        self.mouse_position_world = just_utils.screen_to_world(
                self.__region, self.__rv3d, self.mouse_position)
        self.mouse_vector = just_utils.get_screen_normal(
                self.__region, self.__rv3d, self.mouse_position)
    
    def __update_origins_kd_tree(self):
        kd_data = self.__kd_verts_data["ORIGINS"]["data"]
        for obj in self.__visible_objs:
            k, v, n = self.__get_s2d_w3d_oname(obj.name, obj.location, kd_data)
            kd_data[k] = (v, n)
        self.__kd_tree_from_cache("ORIGINS")
    

    def __get_s2d_w3d_oname(self, o_name, w_vert, kd_data):
        '''返回屏幕座标、世界座标、物体名称'''
        s_vert = just_utils.world_to_screen(self.__region, self.__rv3d, w_vert)
        if s_vert in kd_data:
            # 保留更前面的
            old_v = kd_data[s_vert][0]
            new_v = just_utils.screen_to_world(self.__region, self.__rv3d, s_vert)
            if (w_vert - new_v).length > (old_v - new_v).length:
                o_name = kd_data[s_vert][1]
                w_vert = old_v        

        return s_vert, w_vert, o_name

    def __kd_tree_from_cache(self, snap_type):
        data = self.__kd_verts_data[snap_type]
        kd_data = data["data"]
        len_data = len(kd_data)
        if len_data == 0:
            return
        data["kd"] = kdtree.KDTree(len_data)

        insert = data["kd"].insert
        i = 0
        for k in kd_data.keys():
            insert((*k, 0), i)
            i += 1

        data["kd"].balance()
    
    def __update_view(self):
        # view_distance 与 view_matrix 没有改变则不需要更新数据
        if self.__view_distance == self.__rv3d.view_distance \
                and self.__view_matrix == self.__rv3d.view_matrix:
            return        
        self.__reset_data()

    def __update_kd_tree(self):
        self.__update_view()

        if self.__snap_type == "ORIGINS":
            if self.__kd_verts_data["ORIGINS"]["kd"] is None:
                self.__update_origins_kd_tree()
            return
        
        depsgraph = self.__ctx.evaluated_depsgraph_get()
        hit_objs = []
        snap_data = self.__kd_verts_data[self.__snap_type]
        
        if self.__xray_mode:
            hits = self.__get_objs_under_mouse()
            for _, obj_name in enumerate(hits):
                if hit_object.name not in self.__visible_objs_name and obj_name not in snap_data["objs"]:
                    hit_objs.append({
                        "name": obj_name,
                        "location": None,
                        "index": None
                    })
            if len(hit_objs) == 0:
                return
        else:
            (direct_hit, hit_location, _, face_index, hit_object, _) = self.__ctx.scene.ray_cast(
                    depsgraph, origin=self.mouse_position_world,
                    direction=self.mouse_vector)
            # print(direct_hit, hit_object)
            if direct_hit is False:
                return
            obj_name = hit_object.name
            if obj_name not in self.__visible_objs_name \
                    or obj_name in snap_data["objs"]:
                return
            bm = self.__objs_data["data"][obj_name]["bm"]
            if just_utils.ignore_high_density_mesh(
                    bm.faces[face_index].verts, self.__region, self.__rv3d):
                return
            
            hit_objs.append({
                "name": obj_name,
                "location": hit_location,
                "index": face_index
            })
        # print("重建 kdtree2")            
        for _, item in enumerate(hit_objs):
            obj_name = item["name"]
            # if obj_name not in snap_data["objs"]:
            # print("重建 kdtree2")
            snap_data["objs"].append(obj_name)
            data = {}
            obj_data = self.__objs_data["data"][obj_name]
            ignore_back = not self.__xray_mode
            if self.__snap_type == "POINTS":
                data = just_utils.get_vert_data(
                    obj_data, self.__region, self.__rv3d, 
                    self.__v3d_0_0, self.__v3d_w_h, ignore_back )
            elif self.__snap_type == "MIDPOINTS":
                data = just_utils.get_edge_data(
                    obj_data, self.__region, self.__rv3d, 
                    self.__v3d_0_0, self.__v3d_w_h, ignore_back )
            elif self.__snap_type == "FACES":
                data = just_utils.get_face_data(
                    obj_data, self.__region, self.__rv3d, 
                    self.__v3d_0_0, self.__v3d_w_h, ignore_back )
            if len(data) == 0:
                continue
            snap_data["data"].update(data)
        self.__kd_tree_from_cache(self.__snap_type)

    
    def __reset_data(self):
        '''视角改变时重置数据'''
        # 重置数据
        # print("重置数据")
        # for k in self.__snap_type_list:
        #     d = self.__kd_verts_data[k]
        #     d["data"] = {}
        #     d["objs"] = []
        #     d["kd"] = None


        # data: {
        #     屏幕      世界     名称   下标
        #     (0,0): ( (0,0,0), "name", 0 )  
        # }
        self.__kd_verts_data = {
            "ORIGINS": {
                "data": {},
                "kd": None,
                "objs": []
            },
            "POINTS": {
                "data": {},
                "kd": None,
                "objs": []
            },
            "MIDPOINTS": {
                "data": {},
                "kd": None,
                "objs": []
            },
            "FACES": {
                "data": {},
                "kd": None,
                "objs": []
            },
        }

        self.__view_distance = self.__rv3d.view_distance
        self.__view_matrix = self.__rv3d.view_matrix.copy()

        self.__v3d_0_0 = just_utils.screen_to_world(self.__region, self.__rv3d, (20,20))
        self.__v3d_w_h = just_utils.screen_to_world(self.__region, self.__rv3d, 
            (self.__region.width - 20, self.__region.height-20))
        
        # bpy.data.objects["x0"].location = self.__v3d_0_0
        # bpy.data.objects["x1"].location = self.__v3d_w_h

        # {
        #     名称      最小值      最大值      
        #     "name": ((x0, y0), (x1, y1)) 
        # }
        self.__screen_bound_data = {}

        self.update_xray_mode()
                
    
    def get_snap_point(self, context, event):
        '''获取离鼠标最近的吸附点'''
        # return (
        #   True,           是否吸附成功
        #   (x, y, z),      吸附到的世界座标 Or None
        #   obj_name,       吸附物体名称 Or ""
        #   [(x, y, z) ...] 周围可吸附的最近的点，最多6个
        # )
        self.__update_mouse(event)
        self.__update_kd_tree()
        data = self.__kd_verts_data[self.__snap_type]

        self.xxxx = data["data"]
        # print(data)
        if data["kd"]:
            search_distance = 200 
            points_found = data["kd"].find_range(((self.mouse_position[0], self.mouse_position[1], 0)), search_distance)
            len_found = len(points_found)
            if len_found == 0:
                return False, None, "", []
            elif len_found == 1:
                found = points_found
            else:
                found = sorted(points_found, key=lambda point: point[2])[:6]

            kd_data = data["data"]
            

            closest = None
            if found[0][2] < 20:
                closest = found[0][0]
                k = (floor(closest[0]), floor(closest[1]))
                
                return True, kd_data[k][0], kd_data[k][1], []
            else:
                closest_6 = []
                for fd in found:
                    k = (floor(fd[0][0]), floor(fd[0][1]))
                    closest_6.append(kd_data[k][0])
                return False, None, "", closest_6
        return False, None, "", []

    def update_xray_mode(self):
        xray = False
        shading = self.__space_data.shading
        shading_type = shading.type
        if shading_type == 'WIREFRAME':
            xray = shading.show_xray_wireframe
        elif shading_type == 'SOLID':
            xray = shading.show_xray
        self.__xray_mode = xray

        if xray:
            for obj_name, bound in self.__objs_data["box"].items():

                M = just_utils.matrix_screen_to_matrix_world(self.__rv3d, self.__v3d_0_0)
                isInView, v = just_utils.is_in_view(bound, M, self.__v3d_w_h)
                if isInView:
                    M = M.inverted()
                    minV = M @ Vector((v[0], v[1], 0))
                    maxV = M @ Vector((v[2], v[3], 0))
                    minV = just_utils.world_to_screen(self.__region, self.__rv3d, minV)
                    maxV = just_utils.world_to_screen(self.__region, self.__rv3d, maxV)
                    # print(obj_name, minV, maxV)
                    self.__screen_bound_data[obj_name] = (minV, maxV)



 
                
