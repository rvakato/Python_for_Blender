import bpy
import bmesh

def remove_unused_slots(obj):
    # Remove unused material slots
    used_slots = set()
    for f in obj.data.polygons:
        used_slots.add(f.material_index)
    
    # Remove slots from highest index to lowest
    for i in reversed(range(len(obj.material_slots))):
        if i not in used_slots:
            obj.data.materials.pop(index=i)

# Get the active object (assumes it is already selected)
obj = bpy.context.active_object

if obj:
    # Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Create a new bmesh and load the mesh data
    bm = bmesh.from_edit_mesh(obj.data)
    
    # Deselect all faces
    for f in bm.faces:
        f.select = False
    
    # Iterate through the materials on the object
    for mat_index, mat_slot in enumerate(obj.material_slots):
        # Select the faces that use the current material
        for f in bm.faces:
            if f.material_index == mat_index:
                f.select = True
        
        # Separate the selected faces
        bpy.ops.mesh.separate(type='SELECTED')
        
        # Deselect all faces for the next iteration
        for f in bm.faces:
            f.select = False
    
    # Update the mesh and free the bmesh
    bmesh.update_edit_mesh(obj.data)
    bm.free()
    
    # Exit Edit Mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Remove unused material slots for all separated objects
    for separated_obj in bpy.context.selected_objects:
        remove_unused_slots(separated_obj)
else:
    print("No active object selected.")
