import bpy

# 1. 取得當前選中的物件
active_obj = bpy.context.active_object

if active_obj and active_obj.type == 'MESH':
    # 2. 獲取該物件的面數
    target_face_count = len(active_obj.data.polygons)
    print(f"正在搜尋面數為 {target_face_count} 的物件...")

    # 3. 確保在物件模式
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # 4. 遍歷場景中所有物件
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and obj.data:
            # 檢查面數是否完全相同
            if len(obj.data.polygons) == target_face_count:
                obj.select_set(True)
            else:
                obj.select_set(False)
    
    # 5. 把原本那個物件保持為選中狀態
    bpy.context.view_layer.objects.active = active_obj
    print("選取完成！")
else:
    print("錯誤：請先在畫面中選取一個物件（螺絲）！")