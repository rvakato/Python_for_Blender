import bpy
import os

def link_textures_to_principled(material):
    if not material.use_nodes:
        material.use_nodes = True
    
    nodes = material.node_tree.nodes
    principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    
    if not principled:
        return
    
    for node in nodes:
        if node.type == 'TEX_IMAGE':
            image = node.image
            if not image:
                continue
            
            name = os.path.splitext(image.name)[0].lower()
            
            if name.endswith('_complete'):
                material.node_tree.links.new(node.outputs['Color'], principled.inputs['Base Color'])
            elif name.endswith('_roughness'):
                node.image.colorspace_settings.name = 'Non-Color'
                material.node_tree.links.new(node.outputs['Color'], principled.inputs['Roughness'])
            elif name.endswith('_metalness'):
                node.image.colorspace_settings.name = 'Non-Color'
                material.node_tree.links.new(node.outputs['Color'], principled.inputs['Metallic'])
            elif name.endswith('_normal'):
                node.image.colorspace_settings.name = 'Non-Color'
                normal_map = nodes.new(type='ShaderNodeNormalMap')
                material.node_tree.links.new(node.outputs['Color'], normal_map.inputs['Color'])
                material.node_tree.links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
            elif name.endswith('_emissive'):
                material.node_tree.links.new(node.outputs['Color'], principled.inputs['Emission'])
            elif name.endswith('_alpha'):
                # node.image.colorspace_settings.name = 'Non-Color'
                material.node_tree.links.new(node.outputs['Color'], principled.inputs['Alpha'])
                # Enable alpha in material settings
                # material.blend_method = 'BLEND'

# Get the active object
obj = bpy.context.active_object

# Process all materials on the object
for material_slot in obj.material_slots:
    material = material_slot.material
    if material:
        link_textures_to_principled(material)

print("Texture linking completed.")
