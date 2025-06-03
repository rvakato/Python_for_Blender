import bpy

def rename_remaining_collections():
    collections = bpy.data.collections
    existing_numbers = set()
    
    # First pass: gather existing FL_# numbers
    for collection in collections:
        if collection.name.startswith("FL_"):
            try:
                num = int(collection.name.split("_")[1])
                existing_numbers.add(num)
            except:
                continue
    
    # Find the next available number
    def get_next_number():
        num = 0
        while num in existing_numbers:
            num += 1
        return num
    
    # Second pass: rename only collections that don't follow the FL_# pattern
    for collection in collections:
        if collection.name != "Scene Collection" and not collection.name.startswith("FL_"):
            next_num = get_next_number()
            collection.name = f"FL_{next_num}"
            existing_numbers.add(next_num)

# Run the function
rename_remaining_collections()
