import bpy
import bmesh
from mathutils import Vector
import os

# 全局变量存储 FBX 导出路径
fbx_output_folder = bpy.props.StringProperty(
    name="Output Folder",
    description="Set the output folder for FBX files",
    default="C:/Users/rvaka/Desktop/Project/TEMP",
    subtype='NONE'  # 移除文件夹图标
)

# 功能：将原点设置为几何中心并应用变换
def apply_transform_and_set_origin_to_center(obj):
    if obj.type == 'MESH':  # 确保是网格类型物件
        bpy.context.view_layer.objects.active = obj  # 设置为活动对象

        # 应用物体的变换（确保准确的几何中心）
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # 设置原点到几何中心
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')

# 功能：将原点设置为底部中心并移动到原点
def set_origin_to_bottom_center_and_move_to_origin(obj):
    # 确保处于物件模式
    bpy.ops.object.mode_set(mode='OBJECT')

    # 创建物件的 bmesh 网格数据
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

    # 找到底部中心
    bottom_center = Vector((
        (bbox_corners[0].x + bbox_corners[4].x) / 2,
        (bbox_corners[0].y + bbox_corners[2].y) / 2,
        min(v.z for v in bbox_corners)
    ))

    # 设置新原点
    bpy.context.scene.cursor.location = bottom_center
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

    # 移动物体到世界原点
    obj.location = Vector((0, 0, 0))

# 功能：导出选中的物体为 FBX
def export_fbx(objects, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    for obj in objects:
        if obj.type == 'MESH':  # 只处理网格类型物件
            file_name = f"{obj.name}.fbx"
            file_path = os.path.join(output_folder, file_name)
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.export_scene.fbx(
                filepath=file_path,
                use_selection=True,
                axis_forward='-Z',
                axis_up='Y',
                bake_space_transform=True,
                apply_scale_options='FBX_SCALE_NONE',
                object_types={'MESH'}
            )
            print(f"Exported {obj.name} to {file_path}")

# 操作类：用于导出 FBX 的功能
class EXPORT_OT_fbx_button(bpy.types.Operator):
    bl_idname = "export.fbx_button"
    bl_label = "Export FBX"
    
    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected. Please select mesh objects.")
            return {'CANCELLED'}
        
        output_folder = context.scene.fbx_output_folder
        for obj in selected_objects:
            if obj.type == 'MESH':
                apply_transform_and_set_origin_to_center(obj)
                set_origin_to_bottom_center_and_move_to_origin(obj)
        export_fbx(selected_objects, output_folder)
        self.report({'INFO'}, "FBX Export Completed!")
        return {'FINISHED'}

# 面板类：用于显示导出路径和按钮
class VIEW3D_PT_fbx_export_panel(bpy.types.Panel):
    bl_label = "FBX Exporter"
    bl_idname = "VIEW3D_PT_fbx_exporter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FBX Tools'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 输出路径输入框
        layout.prop(scene, "fbx_output_folder", text="FBX Path")
        
        # 导出按钮
        layout.operator("export.fbx_button", text="Export FBX")

# 注册类和属性
def register():
    bpy.utils.register_class(EXPORT_OT_fbx_button)
    bpy.utils.register_class(VIEW3D_PT_fbx_export_panel)
    bpy.types.Scene.fbx_output_folder = fbx_output_folder

def unregister():
    bpy.utils.unregister_class(EXPORT_OT_fbx_button)
    bpy.utils.unregister_class(VIEW3D_PT_fbx_export_panel)
    del bpy.types.Scene.fbx_output_folder

if __name__ == "__main__":
    register()