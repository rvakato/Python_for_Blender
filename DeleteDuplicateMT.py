import bpy

mats = bpy.data.materials

# Keep track of processed base names to handle multiple numbered variants
processed_bases = {}

for mat in mats:
    # Split the name into base and extension
    (base, _, ext) = mat.name.rpartition(".")
    
    # Check if extension is numeric
    if ext.isnumeric():
        # If we haven't processed this base name yet
        if base not in processed_bases:
            # Store the first numbered material we find
            processed_bases[base] = mat
            # Rename it to the base name (removing the .001, .002 etc)
            mat.name = base
        else:
            # For subsequent materials with same base, remap to the first one
            mat.user_remap(processed_bases[base])
            mats.remove(mat)
