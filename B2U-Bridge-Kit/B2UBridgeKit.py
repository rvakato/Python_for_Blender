import bpy
import bmesh
from mathutils import Vector, Matrix

bl_info = {
    "name": "B2U Bridge Kit",
    "author": "rvakato",
    "version": (1, 2),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > B2U Kit",
    "description": "Recover lost transform data for objects before exporting to Unreal Engine",
    "category": "Object",
}


class B2U_FaceProps(bpy.types.PropertyGroup):
    ref_face_area: bpy.props.FloatProperty(name="Face Area", default=0.0)
    ref_face_perimeter: bpy.props.FloatProperty(name="Face Perimeter", default=0.0)
    ref_face_edge_count: bpy.props.IntProperty(name="Edge Count", default=0)
    ref_local_offset: bpy.props.FloatVectorProperty(name="Local Offset", size=3, default=(0.0, 0.0, 0.0))
    has_reference: bpy.props.BoolProperty(name="Has Reference Face", default=False)


def _find_matching_face(bm, ref_area, ref_perimeter, ref_edge_count):
    best_face = None
    best_score = float('inf')
    for face in bm.faces:
        if len(face.edges) != ref_edge_count:
            continue
        area_rel = abs(face.calc_area() - ref_area) / max(ref_area, 1e-6)
        perim_rel = abs(face.calc_perimeter() - ref_perimeter) / max(ref_perimeter, 1e-6)
        score = area_rel + perim_rel
        if score < best_score:
            best_score = score
            best_face = face
    return best_face, best_score


class B2U_OT_RecordReferenceFace(bpy.types.Operator):
    bl_idname = "b2u.record_reference_face"
    bl_label = "Record Reference Face"
    bl_description = (
        "In Edit Mode, select exactly one face on the reference object. "
        "Records its area, perimeter, edge count, and local offset from the origin. "
        "Run this before Calibrate Orientation"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Enter Edit Mode and select exactly one face first")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        selected_faces = [f for f in bm.faces if f.select]

        if len(selected_faces) != 1:
            self.report({'ERROR'}, f"Select exactly one face ({len(selected_faces)} currently selected)")
            return {'CANCELLED'}

        face = selected_faces[0]
        local_center = face.calc_center_median()

        props = context.scene.b2u_props
        props.ref_face_area = face.calc_area()
        props.ref_face_perimeter = face.calc_perimeter()
        props.ref_face_edge_count = len(face.edges)
        props.ref_local_offset = (local_center.x, local_center.y, local_center.z)
        props.has_reference = True

        self.report({'INFO'}, (
            f"Recorded — area: {props.ref_face_area:.5f}, "
            f"edges: {props.ref_face_edge_count}, "
            f"offset: ({local_center.x:.3f}, {local_center.y:.3f}, {local_center.z:.3f})"
        ))
        return {'FINISHED'}


class B2U_OT_CalibrateOrientation(bpy.types.Operator):
    bl_idname = "b2u.calibrate_orientation"
    bl_label = "Calibrate Orientation"
    bl_description = (
        "Isolates mesh data, sets origin to geometry, then aligns the object to world Z. "
        "Uses the recorded reference face normal if available, otherwise falls back to the two largest faces"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        props = context.scene.b2u_props

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True)
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        # Determine alignment axis from recorded face or fall back to two largest faces
        current_axis = None
        if props.has_reference:
            face, score = _find_matching_face(
                bm, props.ref_face_area, props.ref_face_perimeter, props.ref_face_edge_count
            )
            if face and score <= 0.1:
                current_axis = face.normal.normalized()
            else:
                self.report({'WARNING'}, f"Reference face not found (score {score:.3f}), falling back to largest faces")

        if current_axis is None:
            sorted_faces = sorted(bm.faces, key=lambda f: f.calc_area(), reverse=True)
            if len(sorted_faces) < 2:
                bm.free()
                self.report({'ERROR'}, "Mesh needs at least 2 faces")
                return {'CANCELLED'}
            c1 = sorted_faces[0].calc_center_median()
            c2 = sorted_faces[1].calc_center_median()
            current_axis = (c1 - c2).normalized()

        # Compute geometry centroid for centering (origin_set already centered it, this is a safety pass)
        centroid = Vector((0.0, 0.0, 0.0))
        for v in bm.verts:
            centroid += v.co
        centroid /= len(bm.verts)

        rotation_matrix = current_axis.rotation_difference(Vector((0, 0, 1))).to_matrix().to_4x4()
        translation_matrix = Matrix.Translation(-centroid)
        full_transform = rotation_matrix @ translation_matrix

        bmesh.ops.transform(bm, matrix=full_transform, verts=bm.verts)
        bm.to_mesh(obj.data)
        bm.free()

        obj.rotation_euler = (0, 0, 0)

        # Update stored local offset to reflect the transformed position after calibration
        if props.has_reference:
            old_offset = Vector(props.ref_local_offset)
            new_offset = rotation_matrix.to_3x3() @ (old_offset - centroid)
            props.ref_local_offset = (new_offset.x, new_offset.y, new_offset.z)

        self.report({'INFO'}, f"'{obj.name}' calibrated to world Z")
        return {'FINISHED'}


class B2U_OT_SelectByPolyCount(bpy.types.Operator):
    bl_idname = "b2u.select_by_poly_count"
    bl_label = "Select by Poly Count"
    bl_description = (
        "Selects all mesh objects in the scene whose polygon count matches "
        "the active object. Use to gather all objects of the same type"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active_obj = context.active_object
        if not active_obj or active_obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        target_count = len(active_obj.data.polygons)
        matched = 0

        for obj in context.scene.objects:
            if obj.type == 'MESH' and obj.data:
                match = len(obj.data.polygons) == target_count
                obj.select_set(match)
                if match:
                    matched += 1

        context.view_layer.objects.active = active_obj
        self.report({'INFO'}, f"Selected {matched} object(s) with {target_count} polygons")
        return {'FINISHED'}


class B2U_OT_RecoverAndInstance(bpy.types.Operator):
    bl_idname = "b2u.recover_and_instance"
    bl_label = "Recover and Instance"
    bl_description = (
        "Shift-click the calibrated reference object last to make it active. "
        "Finds the recorded face on each target, infers rotation from its normal, "
        "then places the origin at face_center - (rotation x local_offset)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.b2u_props

        if not props.has_reference:
            self.report({'ERROR'}, "Record a reference face first (Step 1a)")
            return {'CANCELLED'}

        master_obj = context.active_object
        if not master_obj:
            self.report({'ERROR'}, "Shift-click the reference object last to make it active")
            return {'CANCELLED'}

        targets = [obj for obj in context.selected_objects if obj != master_obj and obj.type == 'MESH']
        if not targets:
            self.report({'WARNING'}, "No target objects selected")
            return {'CANCELLED'}

        master_data = master_obj.data
        local_offset = Vector(props.ref_local_offset)
        failed = 0

        for obj in targets:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.faces.ensure_lookup_table()

            face, score = _find_matching_face(
                bm,
                props.ref_face_area,
                props.ref_face_perimeter,
                props.ref_face_edge_count,
            )

            if face is None or score > 0.1:
                self.report({'WARNING'}, f"'{obj.name}': no matching face found (score {score:.3f})")
                bm.free()
                failed += 1
                continue

            # Compute face data in world space before replacing mesh
            face_center_world = obj.matrix_world @ face.calc_center_median()
            face_normal_world = (obj.matrix_world.to_3x3() @ face.normal).normalized()
            bm.free()

            # Rotation: align object Z axis to the face normal
            new_rotation = face_normal_world.to_track_quat('Z', 'Y')

            # Position: back-calculate origin so the matched face lands at face_center_world
            rotated_offset = new_rotation.to_matrix() @ local_offset

            obj.data = master_data
            obj.rotation_mode = 'QUATERNION'
            obj.rotation_quaternion = new_rotation
            obj.location = face_center_world - rotated_offset

        succeeded = len(targets) - failed
        self.report(
            {'INFO'},
            f"Recovered {succeeded} object(s)" + (f", {failed} failed — check face recording" if failed else "")
        )
        return {'FINISHED'}


class B2U_PT_BridgeKit(bpy.types.Panel):
    bl_label = "B2U Bridge Kit"
    bl_idname = "B2U_PT_bridge_kit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "B2U Kit"

    def draw(self, context):
        layout = self.layout
        props = context.scene.b2u_props

        layout.label(text="Step 1a — Record Reference Face")
        layout.operator("b2u.record_reference_face", icon='FACESEL')

        if props.has_reference:
            box = layout.box()
            box.label(text=f"Area:    {props.ref_face_area:.5f}")
            box.label(text=f"Edges:   {props.ref_face_edge_count}")
            o = props.ref_local_offset
            box.label(text=f"Offset:  ({o[0]:.3f}, {o[1]:.3f}, {o[2]:.3f})")

        layout.separator()

        layout.label(text="Step 1b — Calibrate Reference")
        layout.operator("b2u.calibrate_orientation", icon='ORIENTATION_GLOBAL')

        layout.separator()

        layout.label(text="Step 2 — Select Similar Objects")
        layout.operator("b2u.select_by_poly_count", icon='RESTRICT_SELECT_OFF')

        layout.separator()

        layout.label(text="Step 3 — Recover Transforms")
        layout.operator("b2u.recover_and_instance", icon='LINKED')


classes = [
    B2U_FaceProps,
    B2U_OT_RecordReferenceFace,
    B2U_OT_CalibrateOrientation,
    B2U_OT_SelectByPolyCount,
    B2U_OT_RecoverAndInstance,
    B2U_PT_BridgeKit,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.b2u_props = bpy.props.PointerProperty(type=B2U_FaceProps)


def unregister():
    if hasattr(bpy.types.Scene, "b2u_props"):
        del bpy.types.Scene.b2u_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


try:
    unregister()
except Exception:
    pass
register()
