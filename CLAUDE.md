# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

A collection of Blender Python scripts and addons for 3D asset processing, aimed at game engine pipelines (Unreal Engine, Substance Painter). There is no build system, no package manager, and no test framework — code runs directly inside Blender's Python environment.

## How to Install / Run

**Standalone scripts** (no `bl_info`, no register/unregister): paste into Blender's Text Editor and click **Run Script**, or use the Scripting workspace. They execute immediately against `bpy.context`.

**Addon files** (have `bl_info`): install via Blender → Edit → Preferences → Add-ons → Install… → select the `.py` file → enable the checkbox. The addon then appears in the 3D Viewport's N-panel (sidebar).

Files that are addons: `MaterialTools_V1.py`, `makerealexporter.py`, `SetObjectToOrigin.py`, `__init__.py`.

There are no unit tests. `test.py` is an experimental scratch version of the exporter, not a test suite.

## Code Architecture

### Two categories of code

**Addons** — have `bl_info`, `register()`, `unregister()`, operator classes, UI panels, and property groups. They are persistent in Blender's UI and support undo (`bl_options = {'REGISTER', 'UNDO'}`).

**Standalone scripts** — execute top-to-bottom when run. No classes are registered; logic is written procedurally against `bpy.context.selected_objects` / `bpy.context.active_object`.

### Addon structure pattern

Every operator follows this layout:

```python
class NAMESPACE_OT_action(bpy.types.Operator):
    bl_idname = "namespace.action"
    bl_label  = "Button Label"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # work
        return {'FINISHED'}
```

UI panels attach to the 3D Viewport sidebar (`bl_space_type = 'VIEW_3D'`, `bl_region_type = 'UI'`, `bl_category = "Tab Name"`).

Properties live in a `bpy.types.PropertyGroup` subclass and are registered onto `bpy.types.Scene` or `bpy.types.Object`.

### Key files and their purpose

| File | Purpose |
|---|---|
| `MaterialTools_V1.py` | Full-featured addon: remove duplicates, random materials, auto-link textures by suffix |
| `makerealexporter.py` | Addon: converts linked instances to real objects, applies scale, recalculates normals, exports FBX per collection |
| `SetObjectToOrigin.py` | Addon: origin alignment + individual FBX export (axis_forward='-Z', axis_up='Y') |
| `__init__.py` | Simple addon: assigns materials by object name prefix using regex `^(\w+)(?:\.\d+)?$` |
| `B2U-Bridge-Kit/` | Standalone scripts for screw/fastener geometry: alignment, repositioning, polygon-count selection |

### FBX export conventions

- Game-engine axis: `axis_forward='-Z'`, `axis_up='Y'`, `bake_space_transform=True`
- Instances must be converted to real objects before export (`bpy.ops.object.make_single_user`, `bpy.ops.object.duplicates_make_real`)
- After instance conversion, delete all temporary objects by tracking originals before the operation

### Blender API idioms used throughout

- Mode switching: `bpy.ops.object.mode_set(mode='OBJECT')` before any data edits
- Selection manipulation: `obj.select_set(True/False)`, `context.view_layer.objects.active = obj`
- Geometry math via `bmesh` (imported from `import bmesh`)
- Material deduplication: iterate `bpy.data.materials`, use `.user_remap()` to redirect references
- UV layer cleanup: `obj.data.uv_layers.remove(layer)`, keep only the first

## Blender Version Targets

- `MaterialTools_V1.py`: Blender 2.82+
- `makerealexporter.py`: Blender 3.0+
- All other scripts: no declared minimum, assumed 3.x
