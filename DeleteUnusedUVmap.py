import bpy

# Get all selected objects
selected_objects = bpy.context.selected_objects

for obj in selected_objects:
    if obj.type == 'MESH' and obj.data.uv_layers:
        uv_layers = obj.data.uv_layers
        
        # Find the active (displayed) UV map
        active_uv = uv_layers.active
        
        # If there's more than one UV map
        if len(uv_layers) > 1:
            # First, make sure the active UV map is not going to be deleted
            if active_uv != uv_layers[0]:
                uv_layers.active_index = 0
                uv_layers.remove(active_uv)
                active_uv = uv_layers[0]
            
            # Remove all UV maps except the first one (which is now the active one)
            while len(uv_layers) > 1:
                uv_layers.remove(uv_layers[1])
        
        # Rename the remaining UV map to "UVMap"
        if uv_layers:
            uv_layers[0].name = "UVMap"

print("UV map cleanup and renaming completed.")