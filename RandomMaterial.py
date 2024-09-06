import random 
import bpy 
prefix = '_' 
materials = [] 
for mat in bpy.data.materials: 
  if mat.name.startswith(prefix): materials.append(mat) 

for obj in bpy.context.selected_objects: 
  obj.active_material = random.choice(materials)