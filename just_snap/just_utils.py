import bpy
from mathutils import bvhtree
from bpy_extras import view3d_utils
from math import floor


def get_visible_objs(context, is_local=False):
    objects = context.scene.objects
    all_objs = [obj for obj in objects if obj.type == 'MESH' and obj.visible_get()]
    if is_local:
        backup_select_objs = [obj for obj in objects if obj.select_get()]
        backup_active_obj = context.active_object
        bpy.ops.object.select_all(action='SELECT')
        objs = [obj for obj in all_objs if obj.select_get()]
        bpy.ops.object.select_all(action='DESELECT')
        for o in backup_select_objs:
            o.select_set(True)
        context.view_layer.objects.active = backup_active_obj
        return objs
    return all_objs

def world_to_screen(region, rv3d, vert):
    v = view3d_utils.location_3d_to_region_2d(
            region, rv3d, vert)
    return (floor(v[0]), floor(v[1]))

def screen_to_world(region, rv3d, coord):
    return view3d_utils.region_2d_to_origin_3d(
            region, rv3d, coord)

def get_screen_normal(region, rv3d, coord):
    return view3d_utils.region_2d_to_vector_3d(
            region, rv3d, coord)

def matrix_screen_to_matrix_world(rv3d, v3d_0_0):
    rvm = rv3d.view_matrix.copy()
    v3d_0_0 = rvm @ v3d_0_0
    return (
        rvm.Translation(-v3d_0_0)
        @ rvm
    )

def is_in_view(bound_box, matrix, v3d_w_h):
    '''物体边界是否在视图内'''
    # 网格不一定在视图内
    axis_x = []
    axis_y = []
    for loc in bound_box:
        p = matrix @ loc
        axis_x.append(p[0])
        axis_y.append(p[1])
    x0 = min(axis_x)   
    y0 = min(axis_y)
    x1 = max(axis_x)   
    y1 = max(axis_y)
    w = v3d_w_h[0]
    h = v3d_w_h[1]
    isInView = True
    if x0 > w or y0 > h or x1 < 0 or y1 < 0:
        isInView = False
    return isInView, (x0, y0, x1, y1)

def get_vert_idx_in_screen(obj, v3d_0_0, v3d_w_h, rv3d, vertices=None):
    if vertices is None:
        vertices = obj.data.vertices
    matrix = obj.matrix_world
    M = matrix_screen_to_matrix_world(rv3d, v3d_0_0)
    idxs = []
    v3d_w_h = M @ v3d_w_h
    w = v3d_w_h[0]
    h = v3d_w_h[1]
    M = M @ matrix
    for vert in vertices:
        p = M @ vert.co
        isInView = True
        if p[0] < 0 or p[0] > w or p[1] < 0 or p[1] > h:
            isInView = False
        if isInView:
            idxs.append(vert.index)
    return idxs

def get_edge_idx_in_screen(obj, v3d_0_0, v3d_w_h, rv3d, edges=None):
    if edges is None:
        edges = obj.data.edges
    vertices = obj.data.vertices
    matrix = obj.matrix_world
    M = matrix_screen_to_matrix_world(rv3d, v3d_0_0)
    idxs = []
    v3d_w_h = M @ v3d_w_h
    w = v3d_w_h[0]
    h = v3d_w_h[1]
    M = M @ matrix
    for edge in edges:
        i0, i1 = edge.vertices
        center = (vertices[i0].co + vertices[i1].co) / 2
        p = M @ center
        isInView = True
        if p[0] < 0 or p[0] > w or p[1] < 0 or p[1] > h:
            isInView = False
        if isInView:
            idxs.append(edge.index)
    return idxs

def get_face_idx_in_screen(obj, v3d_0_0, v3d_w_h, rv3d, polygons=None):
    '''获取物体在视图内的面索引'''
    # 将窗口matrix转为世界matrix，移动 v3d_0_0 到原点
    # 顶点Y座标小于0或大于屏幕宽度则在屏幕外侧
    if polygons is None:
        polygons = obj.data.polygons

    matrix = obj.matrix_world
    M = matrix_screen_to_matrix_world(rv3d, v3d_0_0)
    idxs = []
    v3d_w_h = M @ v3d_w_h
    w = v3d_w_h[0]
    h = v3d_w_h[1]
    M = M @ matrix
    
    for face in polygons:
        p = M @ face.center
        isInView = True
        if p[0] < 0 or p[0] > w or p[1] < 0 or p[1] > h:
            isInView = False
        if isInView:
            idxs.append(face.index)
    return idxs

def get_visible_vert_idx_from_direction(obj, depsgraph, direction, vertices=None):
    '''返回物体上从方向向量看去的未被遮挡的顶点索引'''
    '''忽略物体间的遮挡，仅计算自身的顶点'''
    # direction, 方向向量，指向物体
    if vertices is None:
        vertices = obj.data.vertices
    idxs = []
    bvh = bvhtree.BVHTree.FromObject(obj, depsgraph)
    size = obj.dimensions.length 
    distance = size * 2
    direction = direction.normalized() @ obj.matrix_local
    direction *= -1
    offset = direction * 0.001
    for vert in vertices:
        start_point = vert.co + offset
        # location, normal, index, distance
        _, _, index, _ = bvh.ray_cast(start_point, direction, distance)
        if index is None:
            idxs.append(vert.index)
    return idxs

def get_visible_edge_idx_from_direction(obj, depsgraph, direction, edges=None):
    '''返回物体上从方向向量看去的未被遮挡的边索引'''
    '''忽略物体间的遮挡，仅计算自身的边'''
    # direction, 方向向量，指向物体
    if edges is None:
        edges = obj.data.edges
    vertices = obj.data.vertices
    idxs = []
    bvh = bvhtree.BVHTree.FromObject(obj, depsgraph)
    size = obj.dimensions.length 
    distance = size * 2
    direction = direction.normalized() @ obj.matrix_local
    direction *= -1
    offset = direction * 0.001
    for edge in edges:
        i0, i1 = edge.vertices
        start_point = (vertices[i0].co + vertices[i1].co) / 2 + offset
        # location, normal, index, distance
        _, _, index, _ = bvh.ray_cast(start_point, direction, distance)
        if index is None:
            idxs.append(edge.index)
    return idxs

def get_visible_face_idx_from_direction(obj, depsgraph, direction, polygons=None):
    '''返回物体上从方向向量看去的未被遮挡的面索引'''
    '''忽略物体间的遮挡，仅计算自身的面'''
    # direction, 方向向量，指向物体
    if polygons is None:
        polygons = obj.data.polygons
    idxs = []
    bvh = bvhtree.BVHTree.FromObject(obj, depsgraph)
    size = obj.dimensions.length 
    distance = size * 2
    direction = direction.normalized() @ obj.matrix_local
    offset = direction * size * 1.5
    for face in polygons:
        end_point = face.center
        start_point = end_point - offset
        # location, normal, index, distance
        _, _, index, _ = bvh.ray_cast(start_point, direction, distance)
        if index == face.index:
            idxs.append(face.index)
    return idxs

def __get_data_before(obj_name, depsgraph, region, rv3d, 
        v3d_0_0=None, v3d_w_h=None, ignore_modifiers=True):
    
    obj = bpy.data.objects[obj_name]
    
    screen_normal = get_screen_normal(region, rv3d, 
            (region.width // 2, region.height // 2))
    data = obj.data
    if not ignore_modifiers:
        data = obj.evaluated_get(depsgraph).data
    
    if v3d_0_0 is None:
        v3d_0_0 = screen_to_world(region, rv3d, (0,0))
    if v3d_w_h is None:
        v3d_w_h = screen_to_world(region, rv3d, (region.width,region.height))
    
    d = (obj.location - v3d_0_0).length * screen_normal
    v3d_0_0 = d + v3d_0_0
    v3d_w_h = d + v3d_w_h
    
    return obj, v3d_0_0, v3d_w_h, screen_normal

def get_vert_data(
            obj_name, depsgraph, region, rv3d, v3d_0_0=None, v3d_w_h=None, 
            ignore_back=True, ignore_modifiers=True):
    obj, v3d_0_0, v3d_w_h, screen_normal = __get_data_before(
            obj_name, depsgraph, region, rv3d, v3d_0_0, v3d_w_h, ignore_modifiers)

    data = obj.data
    vertices = data.vertices

    idxs = get_vert_idx_in_screen(
            obj, v3d_0_0, v3d_w_h, rv3d, vertices)
    if len(idxs) == 0:
        return {}
    if ignore_back:
        # 去除被遮挡的点
        vertices = [data.vertices[i] for i in idxs]
        idxs = get_visible_vert_idx_from_direction(obj, depsgraph, screen_normal, vertices)
        if len(idxs) == 0:
            return {}
    matrix = obj.matrix_world
    rs = {}
    for idx in idxs:
        center = matrix @ data.vertices[idx].co
        v_2d = world_to_screen(region, rv3d, center)
        rs[v_2d] = (center, obj_name, idx)
    
    return rs

def get_edge_data(
            obj_name, depsgraph, region, rv3d, v3d_0_0=None, v3d_w_h=None, 
            ignore_back=True, ignore_modifiers=True):
    obj, v3d_0_0, v3d_w_h, screen_normal = __get_data_before(
            obj_name, depsgraph, region, rv3d, v3d_0_0, v3d_w_h, ignore_modifiers)

    data = obj.data
    vertices = data.vertices
    edges = data.edges
    
    idxs = get_edge_idx_in_screen(
            obj, v3d_0_0, v3d_w_h, rv3d, edges)
    if len(idxs) == 0:
        return {}
    if ignore_back:
        # 去除被遮挡的边
        edges = [data.edges[i] for i in idxs]
        idxs = get_visible_edge_idx_from_direction(obj, depsgraph, screen_normal, edges)
        if len(idxs) == 0:
            return {}
    matrix = obj.matrix_world
    rs = {}
    for idx in idxs:
        i0, i1 = data.edges[idx].vertices
        center = (vertices[i0].co + vertices[i1].co) / 2
        center = matrix @ center
        v_2d = world_to_screen(region, rv3d, center)
        rs[v_2d] = (center, obj_name, idx)
    
    return rs

def get_face_data(
            obj_name, depsgraph, region, rv3d, v3d_0_0=None, v3d_w_h=None, 
            ignore_back=True, ignore_modifiers=True):
    '''获取物体在可视区域内的面中点的对照数据'''
    # return {
    #    屏幕        世界      名称    下标
    #    (x, y) : ( (x, y, z), "name", 0 )
    # }
    obj, v3d_0_0, v3d_w_h, screen_normal = __get_data_before(
            obj_name, depsgraph, region, rv3d, v3d_0_0, v3d_w_h, ignore_modifiers)
    
    matrix = obj.matrix_world

    data = obj.data
    polygons = data.polygons
    
    # 获取物体在视图内的面索引
    idxs = get_face_idx_in_screen(
            obj, v3d_0_0, v3d_w_h, rv3d, polygons)
    if len(idxs) == 0:
        print("err 1")
        return {}

    if ignore_back:
        # 去除被遮挡的面
        polygons = [data.polygons[i] for i in idxs]
        idxs = get_visible_face_idx_from_direction(obj, depsgraph, screen_normal, polygons)
        if len(idxs) == 0:
            print("err 2")
            return {}
    
    rs = {}
    for idx in idxs:
        face = data.polygons[idx]
        center = matrix @ face.center
        v_2d = world_to_screen(region, rv3d, center)
        rs[v_2d] = (center, obj_name, idx)
    
    return rs

def ignore_high_density_mesh(obj, idx, region, rv3d):
    '''忽略高密度网格'''
    # 计算射线投射到的面在屏幕上投影的大小
    # 尺寸小于屏幕像素 60 * 60，忽略
    vertices = obj.data.vertices
    verts_idx = obj.data.polygons[idx].vertices
    axis_x = []
    axis_y = []
    matrix = obj.matrix_world
    
    for i in verts_idx:
        vert = matrix @ vertices[i].co
        p = world_to_screen(region, rv3d, vert)
        axis_x.append(p[0])
        axis_y.append(p[1])
    
    x0 = min(axis_x)   
    y0 = min(axis_y)
    x1 = max(axis_x)   
    y1 = max(axis_y)
    w = x1 - x0
    h = y1 - y0
    if w * h > 3600:
        return False
    return True