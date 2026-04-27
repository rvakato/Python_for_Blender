import bpy
import bmesh
from mathutils import Vector, Matrix

bl_info = {
    "name": "B2U Bridge Kit",
    "author": "rvakato",
    "version": (1, 3),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > B2U Kit",
    "description": "Recover lost transform data for objects before exporting to Unreal Engine",
    "category": "Object",
}


class B2U_FaceProps(bpy.types.PropertyGroup):
    # Primary face — defines main axis (Z) and depth offset for positioning
    ref_face_area: bpy.props.FloatProperty(default=0.0)
    ref_face_perimeter: bpy.props.FloatProperty(default=0.0)
    ref_face_edge_count: bpy.props.IntProperty(default=0)
    ref_local_offset: bpy.props.FloatVectorProperty(size=3, default=(0.0, 0.0, 0.0))
    has_primary: bpy.props.BoolProperty(default=False)

    # Secondary face — resolves roll around the main axis
    ref_face2_area: bpy.props.FloatProperty(default=0.0)
    ref_face2_perimeter: bpy.props.FloatProperty(default=0.0)
    ref_face2_edge_count: bpy.props.IntProperty(default=0)
    has_secondary: bpy.props.BoolProperty(default=False)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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


def _frame_from_two_normals(primary_n, secondary_n):
    """Build an orthonormal frame from two face normals.

    primary_n  → becomes local Z
    secondary_n → projected onto plane ⊥ primary_n, becomes local Y (resolves roll)
    Returns (x, y, z) unit vectors, or None if normals are too parallel.
    """
    z = primary_n.normalized()
    y_raw = secondary_n - secondary_n.dot(z) * z   # remove Z component
    if y_raw.length < 1e-4:
        return None
    y = y_raw.normalized()
    x = y.cross(z)                                  # right-hand: y × z = x
    return x, y, z


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class B2U_OT_RecordPrimaryFace(bpy.types.Operator):
    bl_idname = "b2u.record_primary_face"
    bl_label = "Record Primary Face"
    bl_description = (
        "Edit Mode: select exactly one face. "
        "Defines the main axis (Z) and stores the local offset for depth placement"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Enter Edit Mode and select exactly one face")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        selected = [f for f in bm.faces if f.select]

        if len(selected) != 1:
            self.report({'ERROR'}, f"Select exactly one face ({len(selected)} selected)")
            return {'CANCELLED'}

        face = selected[0]
        c = face.calc_center_median()
        props = context.scene.b2u_props
        props.ref_face_area = face.calc_area()
        props.ref_face_perimeter = face.calc_perimeter()
        props.ref_face_edge_count = len(face.edges)
        props.ref_local_offset = (c.x, c.y, c.z)
        props.has_primary = True

        self.report({'INFO'}, f"Primary recorded — area: {props.ref_face_area:.5f}, edges: {props.ref_face_edge_count}")
        return {'FINISHED'}


class B2U_OT_RecordSecondaryFace(bpy.types.Operator):
    bl_idname = "b2u.record_secondary_face"
    bl_label = "Record Secondary Face"
    bl_description = (
        "Edit Mode: select exactly one face (different from the primary). "
        "Its normal resolves the roll around the main axis, fully locking orientation"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Enter Edit Mode and select exactly one face")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        selected = [f for f in bm.faces if f.select]

        if len(selected) != 1:
            self.report({'ERROR'}, f"Select exactly one face ({len(selected)} selected)")
            return {'CANCELLED'}

        face = selected[0]
        props = context.scene.b2u_props
        props.ref_face2_area = face.calc_area()
        props.ref_face2_perimeter = face.calc_perimeter()
        props.ref_face2_edge_count = len(face.edges)
        props.has_secondary = True

        self.report({'INFO'}, f"Secondary recorded — area: {props.ref_face2_area:.5f}, edges: {props.ref_face2_edge_count}")
        return {'FINISHED'}


class B2U_OT_CalibrateOrientation(bpy.types.Operator):
    bl_idname = "b2u.calibrate_orientation"
    bl_label = "Calibrate Orientation"
    bl_description = (
        "Bakes a canonical orientation into the mesh geometry. "
        "With both faces recorded: fully locks axis + roll. "
        "Primary only: locks axis, guesses roll. "
        "Neither: falls back to two-largest-faces heuristic"
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

        rotation_3x3 = None

        # ── Fully locked: two recorded faces ──────────────────────────────
        if props.has_primary and props.has_secondary:
            pf, ps = _find_matching_face(bm, props.ref_face_area, props.ref_face_perimeter, props.ref_face_edge_count)
            sf, ss = _find_matching_face(bm, props.ref_face2_area, props.ref_face2_perimeter, props.ref_face2_edge_count)

            if pf and sf and ps <= 0.1 and ss <= 0.1:
                frame = _frame_from_two_normals(pf.normal, sf.normal)
                if frame:
                    x, y, z = frame
                    # Rows = local frame axes → maps local frame to canonical axes
                    rotation_3x3 = Matrix([x, y, z])
                else:
                    self.report({'WARNING'}, "Faces are nearly parallel — falling back to primary only")
            else:
                self.report({'WARNING'}, f"Face match failed (p:{ps:.3f} s:{ss:.3f}) — falling back to primary only")

        # ── Primary only: locks axis, roll guessed ────────────────────────
        if rotation_3x3 is None and props.has_primary:
            pf, ps = _find_matching_face(bm, props.ref_face_area, props.ref_face_perimeter, props.ref_face_edge_count)
            if pf and ps <= 0.1:
                rotation_3x3 = pf.normal.normalized().rotation_difference(Vector((0, 0, 1))).to_matrix()
            else:
                self.report({'WARNING'}, f"Primary face not found (score {ps:.3f}) — falling back to largest faces")

        # ── Final fallback: two largest faces ─────────────────────────────
        if rotation_3x3 is None:
            sorted_faces = sorted(bm.faces, key=lambda f: f.calc_area(), reverse=True)
            if len(sorted_faces) < 2:
                bm.free()
                self.report({'ERROR'}, "Mesh needs at least 2 faces")
                return {'CANCELLED'}
            c1 = sorted_faces[0].calc_center_median()
            c2 = sorted_faces[1].calc_center_median()
            rotation_3x3 = (c1 - c2).normalized().rotation_difference(Vector((0, 0, 1))).to_matrix()

        # Centroid for translation (origin_set already centred geometry; this is a safety pass)
        centroid = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)

        full_transform = rotation_3x3.to_4x4() @ Matrix.Translation(-centroid)
        bmesh.ops.transform(bm, matrix=full_transform, verts=bm.verts)
        bm.to_mesh(obj.data)
        bm.free()

        obj.rotation_euler = (0, 0, 0)

        # Update stored primary offset to reflect calibrated geometry position
        if props.has_primary:
            old = Vector(props.ref_local_offset)
            new = rotation_3x3 @ (old - centroid)
            props.ref_local_offset = (new.x, new.y, new.z)

        self.report({'INFO'}, f"'{obj.name}' calibrated to canonical orientation")
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
        "Shift-click the calibrated reference last (active object). "
        "Builds a fully-locked rotation from both recorded faces when available, "
        "then places origin at: face_center - (rotation × local_offset)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.b2u_props

        if not props.has_primary:
            self.report({'ERROR'}, "Record a primary face first (Step 1a)")
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

            pf, ps = _find_matching_face(bm, props.ref_face_area, props.ref_face_perimeter, props.ref_face_edge_count)
            if pf is None or ps > 0.1:
                self.report({'WARNING'}, f"'{obj.name}': primary face not found (score {ps:.3f})")
                bm.free()
                failed += 1
                continue

            primary_n_world = (obj.matrix_world.to_3x3() @ pf.normal).normalized()
            face_center_world = obj.matrix_world @ pf.calc_center_median()

            new_rotation = None

            # ── Fully locked: build frame from both faces ──────────────────
            if props.has_secondary:
                sf, ss = _find_matching_face(bm, props.ref_face2_area, props.ref_face2_perimeter, props.ref_face2_edge_count)
                if sf and ss <= 0.1:
                    secondary_n_world = (obj.matrix_world.to_3x3() @ sf.normal).normalized()
                    frame = _frame_from_two_normals(primary_n_world, secondary_n_world)
                    if frame:
                        x, y, z = frame
                        # Columns = world axes → maps canonical local frame to world
                        new_rotation = Matrix([x, y, z]).transposed().to_quaternion()
                    else:
                        self.report({'WARNING'}, f"'{obj.name}': faces nearly parallel — falling back to primary only")
                else:
                    self.report({'WARNING'}, f"'{obj.name}': secondary face not found (score {ss:.3f}) — falling back to primary only")

            # ── Primary only fallback ──────────────────────────────────────
            if new_rotation is None:
                new_rotation = primary_n_world.to_track_quat('Z', 'Y')

            bm.free()

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


class B2U_OT_SimpleInstance(bpy.types.Operator):
    bl_idname = "b2u.simple_instance"
    bl_label = "Simple Instance"
    bl_description = (
        "Shift-click the master object last to make it active. "
        "Replaces mesh data on all other selected objects with the master's data. "
        "Location and rotation are left completely untouched"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        master_obj = context.active_object
        if not master_obj:
            self.report({'ERROR'}, "Shift-click the master object last to make it active")
            return {'CANCELLED'}

        targets = [obj for obj in context.selected_objects if obj != master_obj and obj.type == 'MESH']
        if not targets:
            self.report({'WARNING'}, "No target objects selected")
            return {'CANCELLED'}

        master_data = master_obj.data
        for obj in targets:
            obj.data = master_data

        self.report({'INFO'}, f"Instanced {len(targets)} object(s) to '{master_obj.name}'")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class B2U_PT_BridgeKit(bpy.types.Panel):
    bl_label = "B2U Bridge Kit"
    bl_idname = "B2U_PT_bridge_kit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "B2U Kit"

    def draw(self, context):
        layout = self.layout
        props = context.scene.b2u_props

        layout.label(text="Step 1a — Primary Face  (Axis)")
        layout.operator("b2u.record_primary_face", icon='FACESEL')
        if props.has_primary:
            box = layout.box()
            box.label(text=f"Area:   {props.ref_face_area:.5f}")
            box.label(text=f"Edges:  {props.ref_face_edge_count}")
            o = props.ref_local_offset
            box.label(text=f"Offset: ({o[0]:.3f}, {o[1]:.3f}, {o[2]:.3f})")

        layout.separator()

        layout.label(text="Step 1b — Secondary Face  (Roll)")
        layout.operator("b2u.record_secondary_face", icon='NORMALS_FACE')
        if props.has_secondary:
            box = layout.box()
            box.label(text=f"Area:   {props.ref_face2_area:.5f}")
            box.label(text=f"Edges:  {props.ref_face2_edge_count}")

        layout.separator()

        layout.label(text="Step 1c — Calibrate Reference")
        layout.operator("b2u.calibrate_orientation", icon='ORIENTATION_GLOBAL')

        layout.separator()

        layout.label(text="Step 2 — Select Similar Objects")
        layout.operator("b2u.select_by_poly_count", icon='RESTRICT_SELECT_OFF')

        layout.separator()

        layout.label(text="Step 3 — Recover Transforms")
        layout.operator("b2u.recover_and_instance", icon='LINKED')

        layout.separator()

        layout.label(text="Simple Instance  (rotation already correct)")
        layout.operator("b2u.simple_instance", icon='MESH_DATA')


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = [
    B2U_FaceProps,
    B2U_OT_RecordPrimaryFace,
    B2U_OT_RecordSecondaryFace,
    B2U_OT_CalibrateOrientation,
    B2U_OT_SelectByPolyCount,
    B2U_OT_RecoverAndInstance,
    B2U_OT_SimpleInstance,
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
