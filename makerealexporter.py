bl_info = {
    "name": "Quick FBX Instance Exporter",
    "author": "Gemini AI",
    "version": (1, 2),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > FBX Export Tab",
    "description": "Convert instances to real mesh, export FBX, and clean up automatically.",
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
    # 新增：專供按集合名稱導出的路徑
    path_by_col: bpy.props.StringProperty(
        name="Col Export Path",
        description="Select the directory for Collection-named exports",
        subtype='DIR_PATH'
    )

# --- 核心邏輯 1：原本的轉換 -> 導出 ---
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
        existing_objects = set(bpy.data.objects)
        original_selection = context.selected_objects.copy()

        bpy.ops.object.duplicate()
        bpy.ops.object.duplicates_make_real()

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
        
        all_objs_now = set(bpy.data.objects)
        garbage_to_remove = all_objs_now - existing_objects
        for obj in garbage_to_remove:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)

        for obj in original_selection:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if original_selection:
            context.view_layer.objects.active = original_selection[0]

        return {'FINISHED'}

# --- 新增核心邏輯 2：按 Collection 名稱導出 ---
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

        # 獲取活動物件或第一個選中物件的 Collection 名稱
        target_obj = context.active_object if context.active_object else context.selected_objects[0]
        
        if not target_obj.users_collection:
            self.report({'ERROR'}, "Object does not belong to any collection.")
            return {'CANCELLED'}
            
        col_name = target_obj.users_collection[0].name
        # 處理資料夾路徑與檔名
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

# --- UI 面板 ---
class VIEW3D_PT_QuickExportPanel(bpy.types.Panel):
    bl_label = "FBX Instance Exporter"
    bl_idname = "VIEW3D_PT_quick_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FBX Export'

    def draw(self, context):
        layout = self.layout
        props = context.scene.simple_export_props
        
        # 區塊 1：原始功能
        box = layout.box()
        box.label(text="Manual Naming Export", icon='FILE_TICK')
        box.prop(props, "path")
        box.prop(props, "name")
        box.operator("object.quick_export_instance", icon='EXPORT', text="PROCESS & EXPORT")
        
        layout.separator()

        # 區塊 2：新增功能 (按 Collection 名稱)
        box = layout.box()
        box.label(text="Export by Collection Name", icon='OUTLINER_COLLECTION')
        box.prop(props, "path_by_col", text="Folder")
        
        # 顯示即時預測的檔名 (提示用)
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