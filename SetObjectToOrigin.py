import bpy
import bmesh
from mathutils import Vector
import os

# Global variable to store FBX output folder path
fbx_output_folder = bpy.props.StringProperty(
    name="Output Folder",
    description="Set the output folder for FBX files",
    default="C:/Users/rvaka/Desktop/Project/TEMP",
    subtype='NONE'  # Remove folder icon
)

# Function: Apply transforms and set origin to the object's center of geometry
def apply_transform_and_set_origin_to_center(obj):
    if obj.type == 'MESH':  # Ensure the object is of type 'MESH'
        bpy.context.view_layer.objects.active = obj  # Set as active object

        # Apply transformations (location, rotation, scale)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Set origin to the center of geometry
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')

# Function: Set origin to the bottom center and move object to world origin
def set_origin_to_bottom_center_and_move_to_origin(obj):
    # Ensure we are in object mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Create a bounding box in world coordinates
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

    # Calculate the bottom center
    bottom_center = Vector((
        (bbox_corners[0].x + bbox_corners[4].x) / 2,
        (bbox_corners[0].y + bbox_corners[2].y) / 2,
        min(v.z for v in bbox_corners)
    ))

    # Set the cursor to the bottom center and update the origin
    bpy.context.scene.cursor.location = bottom_center
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

    # Move the object to the world origin
    obj.location = Vector((0, 0, 0))

# Function: Export selected objects as individual FBX files
def export_fbx(objects, output_folder):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    for obj in objects:
        if obj.type == 'MESH':  # Only process mesh objects
            # Generate a unique file name
            file_name = f"{obj.name}.fbx"
            file_path = os.path.join(output_folder, file_name)

            # Deselect all objects
            bpy.ops.object.select_all(action='DESELECT')

            # Select the current object and set it as active
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            # Export the selected object as FBX
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

# Operator class: Handles the FBX export functionality
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
                # Apply transformations and adjust origins
                apply_transform_and_set_origin_to_center(obj)
                set_origin_to_bottom_center_and_move_to_origin(obj)
        
        # Export the processed objects
        export_fbx(selected_objects, output_folder)
        self.report({'INFO'}, "FBX Export Completed!")
        return {'FINISHED'}

# Panel class: Displays UI elements for FBX export
class VIEW3D_PT_fbx_export_panel(bpy.types.Panel):
    bl_label = "FBX Exporter"
    bl_idname = "VIEW3D_PT_fbx_exporter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FBX Tools'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Input field for output folder path
        layout.prop(scene, "fbx_output_folder", text="FBX Path")
        
        # Export button
        layout.operator("export.fbx_button", text="Export FBX")

# Register classes and properties
def register():
    bpy.utils.register_class(EXPORT_OT_fbx_button)
    bpy.utils.register_class(VIEW3D_PT_fbx_export_panel)
    bpy.types.Scene.fbx_output_folder = fbx_output_folder

# Unregister classes and properties
def unregister():
    bpy.utils.unregister_class(EXPORT_OT_fbx_button)
    bpy.utils.unregister_class(VIEW3D_PT_fbx_export_panel)
    del bpy.types.Scene.fbx_output_folder

if __name__ == "__main__":
    register()
