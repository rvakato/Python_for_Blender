import bpy
import os

# Set the directory where FBX files will be saved
output_dir = r"W:\0223 Hill Group\003_Nexus\02 3D\07 Export\FBX\Block5"

# Ensure the output directory exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Deselect all objects
bpy.ops.object.select_all(action='DESELECT')

# Loop through each collection
for collection in bpy.data.collections:
    # Skip empty collections
    if not collection.objects:
        continue

    # Deselect all before each export
    bpy.ops.object.select_all(action='DESELECT')

    # Select objects in the collection
    for obj in collection.objects:
        obj.select_set(True)

    # Make sure one of the selected objects is active
    bpy.context.view_layer.objects.active = collection.objects[0]

    # Define the filepath
    filepath = os.path.join(output_dir, f"{collection.name}.fbx")

    # Export selected objects as FBX
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        apply_unit_scale=True,
        bake_space_transform=True
    )

    print(f"Exported {collection.name} to {filepath}")
