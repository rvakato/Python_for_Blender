import bpy
import bmesh
from mathutils import Vector

def set_origin_to_bottom_center(obj):
    # Create a bmesh from the object's mesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    
    # Calculate the bounding box
    bbox = [Vector(v) for v in obj.bound_box]
    bbox = [obj.matrix_world @ v for v in bbox]
    
    # Find the bottom center
    bottom_center = Vector((
        (bbox[0].x + bbox[4].x) / 2,
        (bbox[0].y + bbox[2].y) / 2,
        min(v.z for v in bbox)
    ))
    
    # Set the new origin
    obj.matrix_world.translation = bottom_center
    
    # Move the object so that its origin is at Z=0
    obj.location.z = 0

def main():
    # Ensure we're in object mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Get all selected objects
    selected_objects = bpy.context.selected_objects
    
    # Check if any objects are selected
    if not selected_objects:
        print("No objects selected. Please select one or more mesh objects.")
        return

    # Store the active object
    active_obj = bpy.context.active_object

    # Counter for processed objects
    processed_count = 0

    # Process each selected object
    for obj in selected_objects:
        if obj.type == 'MESH':
            # Process the object
            set_origin_to_bottom_center(obj)
            processed_count += 1
        else:
            print(f"Skipping non-mesh object: {obj.name}")

    # Restore the active object
    bpy.context.view_layer.objects.active = active_obj

    # Print summary
    print(f"Processed {processed_count} mesh objects.")

# Run the main function
main()