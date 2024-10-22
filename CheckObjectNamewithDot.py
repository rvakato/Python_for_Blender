import bpy

def select_objects_with_dot():
    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')
    
    # Iterate through all objects in the scene
    for obj in bpy.data.objects:
        # Check if the object's name contains a dot
        if '.' in obj.name:
            # Select the object
            obj.select_set(True)
    
    # Make the selected objects active
    if bpy.context.selected_objects:
        bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]

# Run the function
select_objects_with_dot()
