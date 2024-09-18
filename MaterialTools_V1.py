bl_info = {
    "name": "Material Tools",
    "blender": (2, 82, 0),
    "category": "3D View",
}

import bpy
import random
import os

class RemoveUnusedData:
    @staticmethod
    def delete_duplicate_materials():
        mats = bpy.data.materials
        for mat in mats:
            (original, _, ext) = mat.name.rpartition(".")
            if ext.isnumeric() and mats.find(original) != -1:
                print("%s -> %s" % (mat.name, original))
                mat.user_remap(mats[original])
                mats.remove(mat)

    @staticmethod
    def delete_unused_uv_map():
        selected_objects = bpy.context.selected_objects
        for obj in selected_objects:
            if obj.type == 'MESH' and obj.data.uv_layers:
                uv_layers = obj.data.uv_layers
                active_uv = uv_layers.active
                if len(uv_layers) > 1:
                    if active_uv != uv_layers[0]:
                        uv_layers.active_index = 0
                        uv_layers.remove(active_uv)
                    active_uv = uv_layers[0]
                while len(uv_layers) > 1:
                    uv_layers.remove(uv_layers[1])
                if uv_layers:
                    uv_layers[0].name = "UVMap"
        print("UV map cleanup and renaming completed.")

    @staticmethod
    def remove_unused_material_slots():
        selected_objects = bpy.context.selected_objects
        for obj in selected_objects:
            if obj.type == 'MESH':
                RemoveUnusedData.merge_duplicate_materials(obj)
                RemoveUnusedData.remove_unused_slots(obj)
            else:
                print(f"Skipped non-mesh object: {obj.name}")
        print("Finished processing all selected objects.")

    @staticmethod
    def merge_duplicate_materials(obj):
        if obj.type != 'MESH':
            return
        unique_materials = {}
        material_mapping = {}
        for slot in obj.material_slots:
            if slot.material:
                if slot.material.name not in unique_materials:
                    unique_materials[slot.material.name] = slot.material
                material_mapping[slot.material] = unique_materials[slot.material.name]
        for i, slot in enumerate(obj.material_slots):
            if slot.material:
                obj.material_slots[i].material = material_mapping[slot.material]
        used_materials = set(material_mapping.values())
        for i in range(len(obj.material_slots) - 1, -1, -1):
            if obj.material_slots[i].material not in used_materials:
                obj.data.materials.pop(index=i)
        for mat in bpy.data.materials:
            if mat not in used_materials and mat.users == 0:
                bpy.data.materials.remove(mat)

    @staticmethod
    def remove_unused_slots(obj):
        if obj.type != 'MESH':
            return
        used_indices = set(poly.material_index for poly in obj.data.polygons)
        for i in range(len(obj.material_slots) - 1, -1, -1):
            if i not in used_indices:
                obj.data.materials.pop(index=i)

class RandomMaterial:
    @staticmethod
    def assign_random_material(context):
        prefix = context.scene.material_tools.random_material_prefix
        materials = [mat for mat in bpy.data.materials if mat.name.startswith(prefix)]
        if not materials:
            return {'FINISHED'}
        for obj in context.selected_objects:
            obj.active_material = random.choice(materials)

class AutoLinkTexture:
    @staticmethod
    def link_textures_to_principled(material):
        if not material.use_nodes:
            material.use_nodes = True
        nodes = material.node_tree.nodes
        principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not principled:
            return

        material_tools = bpy.context.scene.material_tools

        for node in nodes:
            if node.type == 'TEX_IMAGE':
                image = node.image
                if not image:
                    continue
                name = os.path.splitext(image.name)[0].lower()

                if name.endswith(material_tools.base_color_suffix):
                    material.node_tree.links.new(node.outputs['Color'], principled.inputs['Base Color'])
                elif name.endswith(material_tools.roughness_suffix):
                    node.image.colorspace_settings.name = 'Non-Color'
                    material.node_tree.links.new(node.outputs['Color'], principled.inputs['Roughness'])
                elif name.endswith(material_tools.metalness_suffix):
                    node.image.colorspace_settings.name = 'Non-Color'
                    material.node_tree.links.new(node.outputs['Color'], principled.inputs['Metallic'])
                elif name.endswith(material_tools.normal_suffix):
                    node.image.colorspace_settings.name = 'Non-Color'
                    normal_map = nodes.new(type='ShaderNodeNormalMap')
                    material.node_tree.links.new(node.outputs['Color'], normal_map.inputs['Color'])
                    material.node_tree.links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])
                elif name.endswith(material_tools.emissive_suffix):
                    material.node_tree.links.new(node.outputs['Color'], principled.inputs['Emission'])
                elif name.endswith(material_tools.alpha_suffix):
                    material.node_tree.links.new(node.outputs['Color'], principled.inputs['Alpha'])

    @staticmethod
    def auto_link_textures():
        obj = bpy.context.active_object
        for material_slot in obj.material_slots:
            material = material_slot.material
            if material:
                AutoLinkTexture.link_textures_to_principled(material)
        print("Texture linking completed.")

    @staticmethod
    def remove_duplicate_textures():
        original_images = {}
        
        for mat in bpy.data.materials:
            if mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        image = node.image
                        name = image.name.rstrip('.001').rstrip('.002')  # Remove numeric suffixes
                        
                        if name in original_images:
                            # Remap to original image
                            node.image = original_images[name]
                            print(f"Remapped {image.name} to {original_images[name].name}")
                        else:
                            # Store as original
                            original_images[name] = image
        
        # Remove unused images
        for img in bpy.data.images:
            if img.users == 0:
                bpy.data.images.remove(img)
                print(f"Removed unused image: {img.name}")

class MATERIAL_TOOLS_Properties(bpy.types.PropertyGroup):
    random_material_prefix: bpy.props.StringProperty(
        name="Prefix",
        description="Prefix for materials to be used in random assignment",
        default="_"
    )
    delete_duplicate_textures: bpy.props.BoolProperty(
        name="Delete duplicate textures (.001, .002)",
        description="Enable to remove duplicate textures when auto-linking",
        default=False
    )
    base_color_suffix: bpy.props.StringProperty(
        name="Base Color Suffix",
        description="Suffix for base color textures",
        default="_complete"
    )
    roughness_suffix: bpy.props.StringProperty(
        name="Roughness Suffix",
        description="Suffix for roughness textures",
        default="_roughness"
    )
    metalness_suffix: bpy.props.StringProperty(
        name="Metalness Suffix",
        description="Suffix for metalness textures",
        default="_metalness"
    )
    normal_suffix: bpy.props.StringProperty(
        name="Normal Suffix",
        description="Suffix for normal textures",
        default="_normal"
    )
    emissive_suffix: bpy.props.StringProperty(
        name="Emissive Suffix",
        description="Suffix for emissive textures",
        default="_emissive"
    )
    alpha_suffix: bpy.props.StringProperty(
        name="Alpha Suffix",
        description="Suffix for alpha textures",
        default="_alpha"
    )

class MATERIAL_TOOLS_PT_Panel(bpy.types.Panel):
    bl_label = "Material Tools"
    bl_idname = "MATERIAL_TOOLS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Material Tools'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        material_tools = scene.material_tools

        # Remove Unused Data
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "remove_unused_data_expand", icon="TRIA_DOWN" if context.scene.remove_unused_data_expand else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Remove Unused Data")
        if context.scene.remove_unused_data_expand:
            box.operator("material_tools.delete_duplicate_materials")
            box.operator("material_tools.delete_unused_uv_map")
            box.operator("material_tools.remove_unused_material_slots")

        # Random Material
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "random_material_expand", icon="TRIA_DOWN" if context.scene.random_material_expand else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Random Material")
        if context.scene.random_material_expand:
            box.prop(material_tools, "random_material_prefix")
            box.operator("material_tools.random_material")

        # Auto Link Texture
        box = layout.box()
        row = box.row()
        row.prop(context.scene, "auto_link_texture_expand", icon="TRIA_DOWN" if context.scene.auto_link_texture_expand else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Auto Link Texture")
        if context.scene.auto_link_texture_expand:
            box.prop(material_tools, "delete_duplicate_textures")
            box.prop(material_tools, "base_color_suffix")
            box.prop(material_tools, "roughness_suffix")
            box.prop(material_tools, "metalness_suffix")
            box.prop(material_tools, "normal_suffix")
            box.prop(material_tools, "emissive_suffix")
            box.prop(material_tools, "alpha_suffix")
            box.operator("material_tools.auto_link_textures")

class MATERIAL_TOOLS_OT_DeleteDuplicateMaterials(bpy.types.Operator):
    bl_idname = "material_tools.delete_duplicate_materials"
    bl_label = "Delete Duplicate Materials"

    def execute(self, context):
        RemoveUnusedData.delete_duplicate_materials()
        return {'FINISHED'}

class MATERIAL_TOOLS_OT_DeleteUnusedUVMap(bpy.types.Operator):
    bl_idname = "material_tools.delete_unused_uv_map"
    bl_label = "Delete Unused UV Map"

    def execute(self, context):
        RemoveUnusedData.delete_unused_uv_map()
        return {'FINISHED'}

class MATERIAL_TOOLS_OT_RemoveUnusedMaterialSlots(bpy.types.Operator):
    bl_idname = "material_tools.remove_unused_material_slots"
    bl_label = "Remove Unused Material Slots"

    def execute(self, context):
        RemoveUnusedData.remove_unused_material_slots()
        return {'FINISHED'}

class MATERIAL_TOOLS_OT_RandomMaterial(bpy.types.Operator):
    bl_idname = "material_tools.random_material"
    bl_label = "Random Material"

    def execute(self, context):
        RandomMaterial.assign_random_material(context)
        return {'FINISHED'}

class MATERIAL_TOOLS_OT_AutoLinkTextures(bpy.types.Operator):
    bl_idname = "material_tools.auto_link_textures"
    bl_label = "Auto Link Texture Map"

    def execute(self, context):
        AutoLinkTexture.auto_link_textures()
        if context.scene.material_tools.delete_duplicate_textures:
            AutoLinkTexture.remove_duplicate_textures()
        return {'FINISHED'}

classes = (
    MATERIAL_TOOLS_Properties,
    MATERIAL_TOOLS_PT_Panel,
    MATERIAL_TOOLS_OT_DeleteDuplicateMaterials,
    MATERIAL_TOOLS_OT_DeleteUnusedUVMap,
    MATERIAL_TOOLS_OT_RemoveUnusedMaterialSlots,
    MATERIAL_TOOLS_OT_RandomMaterial,
    MATERIAL_TOOLS_OT_AutoLinkTextures,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.material_tools = bpy.props.PointerProperty(type=MATERIAL_TOOLS_Properties)
    bpy.types.Scene.remove_unused_data_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.random_material_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.auto_link_texture_expand = bpy.props.BoolProperty(default=False)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.material_tools
    del bpy.types.Scene.remove_unused_data_expand
    del bpy.types.Scene.random_material_expand
    del bpy.types.Scene.auto_link_texture_expand

if __name__ == "__main__":
    register()
