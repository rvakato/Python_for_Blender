import bpy
import os

# --- 1. 屬性儲存 (Properties) ---
class SimpleExportProps(bpy.types.PropertyGroup):
    path: bpy.props.StringProperty(name="Folder", subtype='DIR_PATH')
    name: bpy.props.StringProperty(name="Filename", default="Model_Export")
    path_by_col: bpy.props.StringProperty(name="Col Export Path", subtype='DIR_PATH')

# --- 2. 功能邏輯 (Operators) ---

class OBJECT_OT_ProcessOnly(bpy.types.Operator):
    bl_idname = "object.process_instance_only"
    bl_label = "Process Selection (Keep Result)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not context.selected_objects:
            self.report({'ERROR'}, "Nothing selected.")
            return {'CANCELLED'}

        # --- 核心邏輯修改開始 ---
        
        # 1. 紀錄執行前的所有物件
        old_objs = set(bpy.data.objects)

        # 2. 複製並實體化
        bpy.ops.object.duplicate()
        bpy.ops.object.duplicates_make_real()
        
        # 3. 找出所有「新生成」的物件（包含 Mesh 和 Empty）
        new_objs = [obj for obj in bpy.data.objects if obj not in old_objs]

        # 4. 強制選取所有新物件，並取消選取舊物件
        bpy.ops.object.select_all(action='DESELECT')
        for obj in new_objs:
            obj.select_set(True)
            
        # 5. 清除父級關係 (現在 new_objs 包含了那些 Empty 物件，這步會很有用)
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        
        # 6. 篩選出其中的 Mesh 進行後續處理（法線、縮放等）
        temp_meshes = [obj for obj in new_objs if obj.type == 'MESH']
        
        if temp_meshes:
            bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            
            # 修正法線 (以第一個 Mesh 為 active)
            context.view_layer.objects.active = temp_meshes[0]
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')

        # 7. 最後確保所有新物件 (Mesh + Empty) 都被選中，然後進入隔離模式
        for obj in new_objs:
            obj.select_set(True)
            
        bpy.ops.view3d.localview(frame_selected=True)

        self.report({'INFO'}, f"Processed {len(new_objs)} objects and Isolated.")
        return {'FINISHED'}

class OBJECT_OT_QuickExport(bpy.types.Operator):
    bl_idname = "object.quick_export_instance"
    bl_label = "Direct Export"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.simple_export_props
        if not props.path:
            self.report({'ERROR'}, "Please specify a Folder Path.")
            return {'CANCELLED'}
        if not context.selected_objects:
            self.report({'ERROR'}, "Nothing selected.")
            return {'CANCELLED'}

        # 直接組合路徑並導出目前選取的東西
        save_path = os.path.join(bpy.path.abspath(props.path), props.name + ".fbx")
        
        try:
            # 這裡直接使用 use_selection=True，只會導出你手動選取的物件
            bpy.ops.export_scene.fbx(
                filepath=save_path, 
                use_selection=True, 
                bake_space_transform=True, 
                apply_scale_options='FBX_SCALE_ALL'
            )
            self.report({'INFO'}, f"Direct Export Success: {props.name}.fbx")
        except Exception as e:
            self.report({'ERROR'}, f"Export Failed: {str(e)}")
        
        return {'FINISHED'}

class OBJECT_OT_ExportByCollectionName(bpy.types.Operator):
    bl_idname = "object.export_by_collection_name"
    bl_label = "Export Selected (Auto Name)"
    
    def execute(self, context):
        props = context.scene.simple_export_props
        if not props.path_by_col or not context.selected_objects:
            self.report({'ERROR'}, "Check path or selection.")
            return {'CANCELLED'}
        
        target_obj = context.active_object if context.active_object else context.selected_objects[0]
        if not target_obj.users_collection: return {'CANCELLED'}
            
        col_name = target_obj.users_collection[0].name
        save_path = os.path.join(bpy.path.abspath(props.path_by_col), col_name + ".fbx")

        bpy.ops.export_scene.fbx(filepath=save_path, use_selection=True, bake_space_transform=True, apply_scale_options='FBX_SCALE_ALL')
        self.report({'INFO'}, f"Export Success: {col_name}.fbx")
        return {'FINISHED'}

# --- 3. UI 面板 ---
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
        box.operator("object.process_instance_only", icon='TOOL_SETTINGS', text="PROCESS")
        
        box.separator()
        box.prop(props, "path")
        box.prop(props, "name")
        box.operator("object.quick_export_instance", icon='EXPORT', text="EXPORT")
        
        layout.separator()
        box = layout.box()
        box.label(text="Export by Collection Name", icon='OUTLINER_COLLECTION')
        box.prop(props, "path_by_col", text="Folder")
        row = box.row()
        row.scale_y = 1.5
        row.operator("object.export_by_collection_name", icon='EXPORT', text="EXPORT BY COL NAME")

# --- 4. 暴力執行 (Run Script 模式) ---
classes = (SimpleExportProps, OBJECT_OT_ProcessOnly, OBJECT_OT_QuickExport, OBJECT_OT_ExportByCollectionName, VIEW3D_PT_QuickExportPanel)

for cls in classes:
    if hasattr(bpy.types, cls.__name__):
        try: bpy.utils.unregister_class(cls)
        except: pass

if hasattr(bpy.types.Scene, "simple_export_props"):
    del bpy.types.Scene.simple_export_props

for cls in classes:
    bpy.utils.register_class(cls)

bpy.types.Scene.simple_export_props = bpy.props.PointerProperty(type=SimpleExportProps)

# 強制重繪 UI
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D': area.tag_redraw()

print("FBX Exporter: Clear Parent & Keep Transform Added!")