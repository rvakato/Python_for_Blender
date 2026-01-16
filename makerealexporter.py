bl_info = {
    "name": "Quick FBX Instance Exporter (Enhanced)",
    "author": "Gemini AI",
    "version": (1, 3),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > FBX Export Tab",
    "description": "Make Real, Single User, Apply Scale, Fix Normals, and Export FBX.",
    "category": "Import-Export",
}

import bpy
import os

# --- 屬性儲存 ---
class SimpleExportProps(bpy.types.PropertyGroup):
    path: bpy.props.StringProperty(
        name="Folder",
        description="Select the directory to save the FBX",
        subtype='DIR_PATH'
    )
    name: bpy.props.StringProperty(
        name="Filename",
        description="Enter filename without extension",
        default="Model_Export"
    )
    path_by_col: bpy.props.StringProperty(
        name="Col Export Path",
        description="Select the directory for Collection-named exports",
        subtype='DIR_PATH'
    )

# --- 修改後的核心邏輯：保證恢復層級 ---
class OBJECT_OT_QuickExport(bpy.types.Operator):
    bl_idname = "object.quick_export_instance"
    bl_label = "Process and Export"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.simple_export_props
        if not props.path:
            self.report({'ERROR'}, "Please specify a Folder Path.")
            return {'CANCELLED'}
        if not context.selected_objects:
            self.report({'ERROR'}, "Nothing selected.")
            return {'CANCELLED'}

        save_path = os.path.join(bpy.path.abspath(props.path), props.name + ".fbx")
        
        # 【關鍵 1】記錄場景中原始的所有物件，之後產生的全部刪除
        original_objects = set(bpy.data.objects)
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        # 1. 複製並轉為實體
        bpy.ops.object.duplicate()
        bpy.ops.object.duplicates_make_real()
        
        # 獲取複製品 (確保只對副本進行重算與 Apply Scale)
        temp_objs = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if temp_objs:
            # 2. 批量處理複製品 (不合併，保持層級)
            # Make Single User 避免影響到原始模型數據
            bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True)
            # Apply Scale (只影響複製品)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            
            # 3. 效能優化：一次性進入編輯模式處理法線 (不重複進出模式)
            context.view_layer.objects.active = temp_objs[0]
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')

            # 4. 執行導出
            try:
                bpy.ops.export_scene.fbx(
                    filepath=save_path,
                    use_selection=True,
                    bake_space_transform=True,
                    apply_scale_options='FBX_SCALE_ALL'
                )
                self.report({'INFO'}, f"Export Success: {props.name}.fbx")
            except Exception as e:
                self.report({'ERROR'}, f"Export Failed: {str(e)}")
        
        # 【關鍵 2】恢復原狀：刪除所有在 execute 期間產生的新物件
        # 這樣就不會發生 Empty 消失或 Parent 斷掉的問題，因為我們是直接回到「過去」
        current_objects = set(bpy.data.objects)
        new_garbage = current_objects - original_objects
        
        for obj in new_garbage:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)

        # 5. 恢復原始選取
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selection:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        context.view_layer.objects.active = original_active

        return {'FINISHED'}

# --- 核心邏輯 2：按 Collection 名稱導出 (保持原樣) ---
class OBJECT_OT_ExportByCollectionName(bpy.types.Operator):
    bl_idname = "object.export_by_collection_name"
    bl_label = "Export Selected (Auto Name)"
    bl_description = "Export selected objects using their Collection name as filename"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.simple_export_props
        if not props.path_by_col:
            self.report({'ERROR'}, "Please specify the Collection Export Path.")
            return {'CANCELLED'}
        if not context.selected_objects:
            self.report({'ERROR'}, "Nothing selected.")
            return {'CANCELLED'}

        target_obj = context.active_object if context.active_object else context.selected_objects[0]
        if not target_obj.users_collection:
            self.report({'ERROR'}, "Object does not belong to any collection.")
            return {'CANCELLED'}
            
        col_name = target_obj.users_collection[0].name
        folder_path = bpy.path.abspath(props.path_by_col)
        save_path = os.path.join(folder_path, col_name + ".fbx")

        try:
            bpy.ops.export_scene.fbx(
                filepath=save_path,
                use_selection=True,
                bake_space_transform=True,
                apply_scale_options='FBX_SCALE_ALL'
            )
            self.report({'INFO'}, f"Export Success: {col_name}.fbx")
        except Exception as e:
            self.report({'ERROR'}, f"Export Failed: {str(e)}")

        return {'FINISHED'}

# --- UI 面板 (僅修改此部分) ---
class VIEW3D_PT_QuickExportPanel(bpy.types.Panel):
    bl_label = "FBX Instance Exporter"
    bl_idname = "VIEW3D_PT_quick_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FBX Export'

    def draw(self, context):
        layout = self.layout
        props = context.scene.simple_export_props
        
        box = layout.box()
        box.label(text="Manual Naming Export", icon='FILE_TICK')
        
        # 獨立出的 Process 按鈕放在上方
        box.operator("object.quick_export_instance", icon='TOOL_SETTINGS', text="PROCESS")
        
        box.separator()
        
        box.prop(props, "path")
        box.prop(props, "name")
        
        # 改名後的 Export 按鈕
        box.operator("object.quick_export_instance", icon='EXPORT', text="EXPORT")
        
        layout.separator()

        box = layout.box()
        box.label(text="Export by Collection Name", icon='OUTLINER_COLLECTION')
        box.prop(props, "path_by_col", text="Folder")
        
        target_obj = context.active_object if context.active_object else (context.selected_objects[0] if context.selected_objects else None)
        if target_obj and target_obj.users_collection:
            box.label(text=f"Filename: {target_obj.users_collection[0].name}.fbx", icon='INFO')
        else:
            box.label(text="Filename: (Select an object)", icon='ERROR')

        row = box.row()
        row.scale_y = 1.5
        row.operator("object.export_by_collection_name", icon='EXPORT', text="EXPORT BY COL NAME")

# --- 註冊 ---
classes = (
    SimpleExportProps,
    OBJECT_OT_QuickExport,
    OBJECT_OT_ExportByCollectionName,
    VIEW3D_PT_QuickExportPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.simple_export_props = bpy.props.PointerProperty(type=SimpleExportProps)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.simple_export_props

if __name__ == "__main__":
    register()