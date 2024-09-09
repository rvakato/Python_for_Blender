import bpy

def merge_duplicate_materials(obj):
    if obj.type != 'MESH':
        return

    # Dictionary to store unique materials
    unique_materials = {}
    materials_to_remove = []

    # First pass: identify unique and duplicate materials
    for slot in obj.material_slots:
        if slot.material:
            if slot.material.name not in unique_materials:
                unique_materials[slot.material.name] = slot.material
            else:
                materials_to_remove.append(slot.material)

    # Second pass: remap faces using duplicate materials
    if obj.data.polygons and obj.data.materials:
        for poly in obj.data.polygons:
            mat = obj.data.materials[poly.material_index]
            if mat in materials_to_remove:
                # Find the corresponding unique material
                unique_mat = unique_materials[mat.name]
                # Update the material index for this face
                poly.material_index = obj.data.materials.find(unique_mat.name)

    # Remove duplicate materials from the object
    for mat in materials_to_remove:
        index = obj.data.materials.find(mat.name)
        if index >= 0:
            obj.data.materials.pop(index=index)

    # Remove unused materials from the blend file
    for mat in materials_to_remove:
        if mat.users == 0:
            bpy.data.materials.remove(mat)

    print(f"Merged duplicate materials for object: {obj.name}")

# Get the active object
obj = bpy.context.active_object

# Merge duplicate materials for the active object
merge_duplicate_materials(obj)