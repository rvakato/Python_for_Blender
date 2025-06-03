import bpy

# Iterate through the selected objects
for obj in bpy.context.selected_objects:
    # Ensure the object is of type 'MESH'
    if obj.type == 'MESH':
        # Check if the object has material slots
        if obj.material_slots:
            # Get the name of the first material, or assign "No_Material" if no material is assigned
            material_name = obj.material_slots[0].material.name if obj.material_slots[0].material else "No_Material"
            # Rename the object based on the material name
            obj.name = f"{material_name}_Object"
        else:
            # If no material slots are present, assign a default name
            obj.name = "No_Material_Object"