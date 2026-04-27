# B2U-Bridge-Kit

Scripts for preparing Blender assets before exporting to Unreal Engine. All scripts are standalone — run them from Blender's Text Editor (Scripting workspace → Run Script).

## Overview

These three scripts are designed to **recover lost transform data** (location and rotation) for objects such as screws. When transform data is missing or corrupt, spatial orientation cannot be read directly from the object — so these scripts infer it from the geometry itself.

The workflow has three stages:
1. **Calibrate** one reference object to a standard orientation using its geometry
2. **Select** all similar objects by matching polygon count
3. **Reconstruct** location and rotation for each object from its geometric features, then convert them all into instances of the reference

---

## Main Addon

### `B2UBridgeKit.py` — Recommended
Install as a Blender addon (Preferences → Add-ons → Install) or run it once from the Text Editor to register it for the session. Opens a panel under **View3D → Sidebar → B2U Kit** with one button per step.

The panel labels the steps explicitly so the workflow order is always visible:

| Button | Step |
|---|---|
| Record Primary Face | Step 1a |
| Record Secondary Face | Step 1b |
| Calibrate Orientation | Step 1c |
| Select by Poly Count | Step 2 |
| Recover and Instance | Step 3 |
| Simple Instance | — |

**Two-face system for full orientation lock:**
- **Primary face** — defines the main axis (Z) and stores the local offset used for depth placement
- **Secondary face** — its normal is projected onto the plane perpendicular to the primary axis to resolve roll, fully locking the coordinate frame for asymmetric geometry

**Simple Instance** is a standalone utility (no step number) for objects whose rotation and position are already correct — it only replaces mesh data with the master's, anchoring each object to its own existing origin without touching any transforms.

**Calibrate Orientation** bakes a canonical orientation into the mesh using both faces. After calibration, the stored local offset is automatically updated to reflect the face's new position. Fallback chain: two faces → primary only (roll guessed) → two largest faces.

---

## Standalone Scripts

The individual `.py` files remain available to run separately from the Text Editor if needed.

### `CalibrateOrientation.py`
**Purpose:** Calibrates a single object to a standard orientation so it can serve as a reliable reference for the batch step.

**How it works:**
- Ensures object mode, isolates mesh data (`make_single_user`), and sets origin to geometry center — all automatically before doing any geometry work
- Finds the two largest faces (screw head top and tip bottom), computes the axis between their centers
- Rotates the geometry (via bmesh) so that axis aligns to world Z
- Bakes the correction into the mesh data and resets the object transform to `(0, 0, 0)`

**Usage:** Select one object → Run Script.

---

### `SelectByPolyCount.py`
**Purpose:** Selects all mesh objects in the scene whose polygon count matches the active object.

**Usage:** Select the reference object → Run Script. All objects with the same face count become selected.

---

### `RecoverAndInstance.py`
**Purpose:** Batch-recovers location and rotation for all selected objects by inferring orientation from geometry, then converts them into instances of the reference object.

**How it works:**
- The **last selected** (active) object is the reference — its mesh data is the template
- Reads each target object's axis direction from its two largest faces in world space
- Replaces mesh data with the reference and re-applies the inferred orientation as a quaternion rotation
- Result: all selected objects share one mesh (linked instances) with correctly recovered transforms

**Note:** Uses the two-largest-faces heuristic. The panel addon (`B2UBridgeKit.py`) uses the improved face-matching + local offset approach instead — use that for more precise depth placement.

**Usage:** Select all target objects, then **Shift-click the reference object last** to make it active → Run Script.

---

## Workflow

1. Enter Edit Mode on the reference object, select the **primary face** (e.g. top face), run **Record Primary Face** — stores area, perimeter, edge count, and local offset.
2. Still in Edit Mode, select the **secondary face** (any non-parallel face, e.g. a side face), run **Record Secondary Face** — stores its properties for roll resolution.
3. Back in Object Mode, run **Calibrate Orientation** — builds a fully-locked canonical frame from both face normals and bakes it into the mesh. The stored local offset updates automatically.
4. Run **Select by Poly Count** to select all similar objects across the scene.
5. Shift-click the reference last to make it active, run **Recover and Instance** — matches both faces on each target, builds a full rotation frame, and places the origin at `face_center - (rotation × local_offset)`.
6. Export via the main exporter addons in the repo root.
