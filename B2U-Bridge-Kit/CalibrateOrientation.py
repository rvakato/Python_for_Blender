import bpy
import bmesh
from mathutils import Vector, Matrix

def flatten_screw_geometry():
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        print("請選取一個網格物件")
        return

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

    # 1. 使用 BMesh 取得面資訊
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    # 2. 找到面積最大的兩個面 (通常是螺絲頭頂與螺絲尾底)
    sorted_faces = sorted(bm.faces, key=lambda f: f.calc_area(), reverse=True)
    if len(sorted_faces) < 2:
        bm.free()
        return

    f1 = sorted_faces[0]
    f2 = sorted_faces[1]

    # 3. 計算這兩個面的中心點
    c1 = f1.calc_center_median()
    c2 = f2.calc_center_median()

    # 4. 計算目前的中心軸向量
    current_axis = (c1 - c2).normalized()

    # 5. 定義目標向量 (我們要讓螺絲站直，所以目標是 Z 軸)
    target_axis = Vector((0, 0, 1))

    # 6. 計算從「目前的歪軸」轉到「目標 Z 軸」的旋轉矩陣
    rotation_matrix = current_axis.rotation_difference(target_axis).to_matrix().to_4x4()

    # 7. 計算幾何中心，以便將模型移回原點
    geom_center = (c1 + c2) / 2
    translation_matrix = Matrix.Translation(-geom_center)

    # 8. 執行變換：先平移到原點，再旋轉轉正
    full_transform = rotation_matrix @ translation_matrix
    bmesh.ops.transform(bm, matrix=full_transform, verts=bm.verts)

    # 將修改後的數據寫回 Mesh
    bm.to_mesh(obj.data)
    bm.free()
    
    # 9. 重置物件本身的旋轉值為 0 (因為幾何已經轉正了)
    obj.rotation_euler = (0, 0, 0)
    
    print("螺絲幾何已校正：目前幾何已對齊 Z 軸並移至原點。")

flatten_screw_geometry()