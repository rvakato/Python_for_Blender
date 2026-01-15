bl_info = {
    "name": "Quick FBX Instance Exporter",
    "author": "Gemini AI",
    "version": (1, 1),
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

# --- 核心邏輯：轉換 -> 導出 -> 徹底清理 ---
class OBJECT_OT_QuickExport(bpy.types.Operator):
    bl_idname = "object.quick_export_instance"
    bl_label = "Process and Export"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.simple_export_props
        
        # 檢查路徑與選取
        if not props.path:
            self.report({'ERROR'}, "Please specify a Folder Path.")
            return {'CANCELLED'}
        if not context.selected_objects:
            self.report({'ERROR'}, "Nothing selected.")
            return {'CANCELLED'}

        save_path = os.path.join(bpy.path.abspath(props.path), props.name + ".fbx")

        # 1. 紀錄快照 (Snapshot) 以便後續清理
        existing_objects = set(bpy.data.objects)
        original_selection = context.selected_objects.copy()

        # 2. 複製物件 (避免破壞原始場景)
        bpy.ops.object.duplicate()
        
        # 3. 轉換實體 (Make Real)
        # 此操作會產生新物件（包含 Mesh 與可能的 Empty）
        bpy.ops.object.duplicates_make_real()

        # 4. 執行導出 (僅導出選中的新物件)
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
        
        # 5. 徹底清理 (比對快照，刪除所有新產生的物件)
        all_objs_now = set(bpy.data.objects)
        garbage_to_remove = all_objs_now - existing_objects

        for obj in garbage_to_remove:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)

        # 6. 恢復原始選取狀態
        for obj in original_selection:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if original_selection:
            context.view_layer.objects.active = original_selection[0]

        return {'FINISHED'}

# --- UI 面板 ---
class VIEW3D_PT_QuickExportPanel(bpy.types.Panel):
    bl_label = "FBX Instance Exporter"
    bl_idname = "VIEW3D_PT_quick_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FBX Export'  # N-Panel 標籤名稱

    def draw(self, context):
        layout = self.layout
        props = context.scene.simple_export_props
        
        col = layout.column(align=True)
        col.label(text="Output Settings:")
        col.prop(props, "path")
        col.prop(props, "name")
        
        layout.separator()
        
        # 按鈕
        row = layout.row()
        row.scale_y = 1.5
        row.operator("object.quick_export_instance", icon='EXPORT', text="PROCESS & EXPORT")

# --- 註冊 ---
classes = (
    SimpleExportProps,
    OBJECT_OT_QuickExport,
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