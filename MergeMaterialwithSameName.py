import bpy

def merge_duplicate_materials(obj):
    if obj.type != 'MESH':
        return

    # Dictionary to store unique materials
    unique_materials = {}
    material_mapping = {}

    # First pass: identify unique materials and create mapping
    for slot in obj.material_slots:
        if slot.material:
            if slot.material.name not in unique_materials:
                unique_materials[slot.material.name] = slot.material
            material_mapping[slot.material] = unique_materials[slot.material.name]

    # Second pass: update material slots and face assignments
    for i, slot in enumerate(obj.material_slots):
        if slot.material:
            obj.material_slots[i].material = material_mapping[slot.material]

    if obj.data.materials:
        for i, mat in enumerate(obj.data.materials):
            if mat:
                obj.data.materials[i] = material_mapping[mat]

    # Update face material indices
    if obj.data.polygons:
        for poly in obj.data.polygons:
            old_mat = obj.data.materials[poly.material_index]
            new_mat = material_mapping[old_mat]
            poly.material_index = obj.data.materials.find(new_mat.name)

    # Remove unused materials from the object
    used_materials = set(material_mapping.values())
    for i in range(len(obj.material_slots) - 1, -1, -1):
        if obj.material_slots[i].material not in used_materials:
            obj.data.materials.pop(index=i)

    # Remove unused materials from the blend file
    for mat in bpy.data.materials:
        if mat not in used_materials and mat.users == 0:
            bpy.data.materials.remove(mat)

    print(f"Merged duplicate materials for object: {obj.name}")

def remove_unused_material_slots(obj):
    if obj.type != 'MESH':
        return

    # Get a set of material indices actually used by the mesh
    used_indices = set(poly.material_index for poly in obj.data.polygons)

    # Remove material slots that are not used
    for i in range(len(obj.material_slots) - 1, -1, -1):
        if i not in used_indices:
            obj.data.materials.pop(index=i)

    print(f"Removed unused material slots for object: {obj.name}")

# Get the active object
obj = bpy.context.active_object

# Merge duplicate materials for the active object
merge_duplicate_materials(obj)

# Remove unused material slots
remove_unused_material_slots(obj)
