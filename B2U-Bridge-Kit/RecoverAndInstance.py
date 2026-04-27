import bpy
import bmesh
from mathutils import Vector

def batch_instance_and_align():
    # 1. 取得基準螺絲 (Active Object)
    master_obj = bpy.context.active_object
    if not master_obj:
        print("請選取基準螺絲作為最後一個物件")
        return
        
    master_data = master_obj.data
    # 取得選中的其他物件
    targets = [obj for obj in bpy.context.selected_objects if obj != master_obj]

    for obj in targets:
        if obj.type != 'MESH': continue
        
        # 2. 在替換數據前，先計算這顆歪螺絲目前的幾何朝向
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        # 抓最大的兩個面
        sorted_faces = sorted(bm.faces, key=lambda f: f.calc_area(), reverse=True)
        
        if len(sorted_faces) >= 2:
            f1 = sorted_faces[0]
            f2 = sorted_faces[1]
            
            # 計算中心連線向量 (世界座標)
            # 注意：這裡要用 obj.matrix_world 來轉換幾何中心
            c1 = obj.matrix_world @ f1.calc_center_median()
            c2 = obj.matrix_world @ f2.calc_center_median()
            
            # 這是原本歪掉的方向向量
            direction = (c1 - c2).normalized()
            
            # 計算物件中心點
            center_pos = (c1 + c2) / 2
            
            # 3. 關鍵動作：替換數據為基準螺絲 (變成 Instance)
            obj.data = master_data
            
            # 4. 重新賦予旋轉與位置
            # 我們讓基準螺絲的 Z 軸對齊剛剛算出來的向量
            obj.rotation_mode = 'QUATERNION'
            obj.rotation_quaternion = direction.to_track_quat('Z', 'Y')
            obj.location = center_pos
            
        bm.free()

    print(f"完成！已處理 {len(targets)} 顆螺絲。")

batch_instance_and_align()