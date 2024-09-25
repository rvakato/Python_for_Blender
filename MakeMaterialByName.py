import bpy
import re

class MaterialAssignmentProperties(bpy.types.PropertyGroup):
    prefix: bpy.props.StringProperty(
        name="Material Prefix",
        description="Prefix for material names",
        default="T_"
    )

class OBJECT_OT_assign_materials(bpy.types.Operator):
    bl_idname = "object.assign_materials"
    bl_label = "Assign Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        prefix = context.scene.material_assignment_props.prefix

        def create_material_slot(name):
            mat = bpy.data.materials.get(name)
            if mat is None:
                mat = bpy.data.materials.new(name=name)
            return mat

        def assign_material_slot(obj, mat_name):
            if obj.data.materials:
                obj.data.materials[0] = create_material_slot(mat_name)
            else:
                obj.data.materials.append(create_material_slot(mat_name))

        material_map = {}
        pattern = r'^(\w+)(?:\.\d+)?$'
        selected_objects = context.selected_objects

        for obj in selected_objects:
            if obj.type == 'MESH':
                match = re.match(pattern, obj.name)
                if match:
                    base_name = match.group(1)
                    if base_name not in material_map:
                        material_map[base_name] = f"{prefix}{base_name}"
                    assign_material_slot(obj, material_map[base_name])

        self.report({'INFO'}, f"Material slots assigned to {len(selected_objects)} objects!")
        return {'FINISHED'}

class VIEW3D_PT_material_assignment(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Material Assignment'
    bl_label = "Material Assignment"

    def draw(self, context):
        layout = self.layout
        props = context.scene.material_assignment_props

        layout.prop(props, "prefix")
        layout.operator("object.assign_materials")

classes = (
    MaterialAssignmentProperties,
    OBJECT_OT_assign_materials,
    VIEW3D_PT_material_assignment
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.material_assignment_props = bpy.props.PointerProperty(type=MaterialAssignmentProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.material_assignment_props

if __name__ == "__main__":
    register()