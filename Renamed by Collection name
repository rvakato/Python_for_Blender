import bpy

def is_correctly_named(obj, collection_name):
    # Check if object name matches pattern "collection_name_001"
    expected_name = f"{collection_name}_001"
    return obj.name == expected_name

def rename_selected_objects_in_collections():
    # Get selected objects
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        print("No objects selected.")
        return
    
    # Create a dictionary to store objects by collection
    collection_objects = {}
    
    # Group selected objects by their collection
    for obj in selected_objects:
        # Get the immediate parent collection of the object
        parent_collection = None
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                parent_collection = collection
                break
                
        if parent_collection:
            if parent_collection.name not in collection_objects:
                collection_objects[parent_collection.name] = []
            collection_objects[parent_collection.name].append(obj)
    
    # Rename objects in each collection
    for collection_name, objects in collection_objects.items():
        # Skip if collection has only one object and it's already correctly named
        if len(objects) == 1 and is_correctly_named(objects[0], collection_name):
            continue
            
        # Sort objects to ensure consistent ordering
        sorted_objects = sorted(objects, key=lambda obj: obj.name)
        
        # Rename objects with incremental numbers
        for index, obj in enumerate(sorted_objects, start=1):
            new_name = f"{collection_name}_{str(index).zfill(3)}"
            obj.name = new_name

# Run the script
rename_selected_objects_in_collections()
