import bpy

def create_vertex_groups_for_selected():
    # Get all selected mesh objects
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not selected_objects:
        print("No mesh objects selected")
        return
    
    for obj in selected_objects:
        # Check if vertex group already exists
        if obj.name not in obj.vertex_groups:
            # Create a vertex group with the same name as the object
            vg = obj.vertex_groups.new(name=obj.name)
            
            # Get all vertex indices
            vertices = [v.index for v in obj.data.vertices]
            
            # Assign all vertices to the vertex group with weight 1.0
            vg.add(vertices, 1.0, 'REPLACE')
            
            print(f"Created vertex group '{obj.name}' for object '{obj.name}'")
        else:
            print(f"Vertex group '{obj.name}' already exists for object '{obj.name}'")

# Run the function
create_vertex_groups_for_selected()
