import bpy
import bmesh
from mathutils import Vector

def set_origin_to_bottom_center(obj):
    # Ensure we're in object mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Create a bmesh from the object's mesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)  # Apply object's transform to bmesh

    # Calculate the bounding box
    bbox_corners = [Vector(v) for v in obj.bound_box]
    bbox_corners = [obj.matrix_world @ v for v in bbox_corners]

    # Find the bottom center
    bottom_center = Vector((
        (bbox_corners[0].x + bbox_corners[4].x) / 2,
        (bbox_corners[0].y + bbox_corners[2].y) / 2,
        min(v.z for v in bbox_corners)
    ))

    # Set the new origin
    bpy.context.scene.cursor.location = bottom_center
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

def main():
    # Store the current selection and active object
    original_selection = bpy.context.selected_objects
    original_active = bpy.context.active_object

    # Ensure we're in object mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Process each selected object
    for obj in original_selection:
        if obj.type == 'MESH':  # Only process mesh objects
            # Make the current object active
            bpy.context.view_layer.objects.active = obj
            # Deselect all objects
            bpy.ops.object.select_all(action='DESELECT')
            # Select only the current object
            obj.select_set(True)
            
            # Set origin to bottom center
            set_origin_to_bottom_center(obj)

    # Restore original selection and active object
    bpy.ops.object.select_all(action='DESELECT')
    for obj in original_selection:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = original_active

    # Reset the 3D cursor position
    bpy.context.scene.cursor.location = Vector((0, 0, 0))

# Run the main function
main()