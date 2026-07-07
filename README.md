# MAXRIG PRO (Open Beta) 🚀
for Autodesk 3ds Max 2025+

**Advanced Auto-Rigging & Animation Retargeting Suite for 3ds Max**

MAXRIG PRO is a modular Python-based toolset designed to bridge the gap between custom FBX/BVH motion data and standard 3ds Max bone systems. It automates rig building, skin transfer, and complex animation retargeting through a data-driven JSON pipeline.


> **Version:** 0.0.1 Beta  
> **Author:** Iman Shirani  
> **Requires:** Autodesk 3ds Max 2025+ · Python 3.10+ · PySide6

[![Donate ❤️](https://img.shields.io/badge/Donate-PayPal-00457C?style=flat-square&logo=paypal&logoColor=white)](https://www.paypal.com/donate/?hosted_button_id=LAMNRY6DDWDC4)
![3dsmax](https://img.shields.io/badge/Autodesk-3ds%20Max-0696D7?style=flat-square&logo=autodesk)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?style=flat-square&logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---
## ⚠️ Beta Note (Known Issues)
* **FBX Rotation Inconsistencies:** Some FBX files may require manual adjustment via the **Live Calibrator** due to varied coordinate systems.
* **Undo History:** Large skin transfer operations might take a moment to register in the undo buffer.
--------------------------

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Standard Rig Builder** | Creates clean Max Bone objects aligned to any FBX skeleton using a JSON profile |
| **Animation Retargeting** | Retargets BVH and FBX motion files to your rig using Orientation Constraints |
| **Pose Correction** | Per-bone transform matrix in JSON for T-pose ↔ A-pose correction |
| **Mirror Bones** | Copy Left → Right (or Right → Left) with delta-from-bind-pose math |
| **Skin Transfer** | Auto-replaces FBX bones with Standard rig bones in Skin modifiers |
| **Visual Calibrator** | Interactive ghost helper to tune per-bone transform matrices |
| **Ghost Helpers** | Pink/red Point helpers for visual alignment checking |
| **BVH Parser** | Pure Python BVH importer (no Max hang, correct Z-up axis) |
| **Auto Scale** | Matches source skeleton height to target rig automatically |
| **Validation Loop** | Pre-build checker with auto-fix and manual override |
| **Multi-Profile** | Supports Mixamo, ACCURIG, Cascadur, Rokoko out of the box |

---

## Supported Rigs / Profiles

| Profile | Rig Source | Notes |
|---------|-----------|-------|
| `Profile_Mixamo.json` | Mixamo FBX (T-pose) | Standard `mixamorig:` prefix |
| `Profile_ACCURIG.json` | AccuRIG / Reallusion (T-pose) | `CC_Base_` prefix bones |
| `Profile_Cascadur.json` | Cascadur (A-pose) | `_l` / `_r` suffix, 65 bones |
| `Profile_Rokoko.json` | Rokoko Smartsuit | No finger bones |

---

## 📦 Installation

### Method 1 — Script (Development)

1. Copy the project folder to your **3ds Max scripts** directory.
2. Launch `maxrigpro.py` from the **Scripting > Run Script...** menu.
3. Set your material root folder from **Settings**.

### Method 2 — Startup Script

Installing the plugin is quick and requires no manual setup in 3ds Max.

1. **Unzip** the downloaded package.
2. **Copy** the `.bundle` folder to the Autodesk Application Plugins directory:
   ```text
   C:\ProgramData\Autodesk\ApplicationPlugins

---

## Quick Start

### Build a Standard Rig

1. Import your FBX character into 3ds Max (with skeleton).
2. In MAXRIG PRO → click **📂 Load Configuration (JSON)** → select the matching profile (e.g. `Profile_Mixamo.json`).
3. Click **✏️ Edit Mapping / Bone Names** to verify bone alignment. Status column shows `OK` (green) or `MISSING` (red) per bone.
4. Click **🚀 BUILD STANDARD RIG**.
5. A hierarchy of clean Max Bones is created, parented under a Dummy root named after the rig.

### Retarget an Animation

1. Complete the **Build a Standard Rig** steps above.
2. Open **🎬 Open Batch Retargeter**.
3. Click **📂 Import Data (FBX/BVH)** → select your motion file.
4. Click **✨ Auto-Guess** to auto-map source bones to target aliases.
5. *(BVH only)* Click **Insert Ref Frame** to create a clean T-pose at frame 0.
6. *(A-pose source)* Click **🙆 Fix Arms** to rotate arms up.
7. Click **📏 Auto-Scale** to match heights.
8. Click **🔗 LINK RIG (Fixed Orient)** → animation is live-driven via Orientation Constraints.

---

## UI Reference

### Main Panel

| Button | Function |
|--------|----------|
| 📂 Load Configuration (JSON) | Load a rig profile JSON file |
| ✏️ Edit Mapping / Bone Names | Open the Mapping Editor |
| 👻 Create Ghosts (Check Alignment) | Create pink Point helpers at bone positions for visual check |
| Show Debug Helpers (Red Points) | Toggle additional red debug points |
| 🔓 UNLOCK BONES (Edit Placement) | Disable Skin modifier so bones can be moved |
| 🔒 LOCK BONES (Apply Fix) | Re-enable Skin modifier and update bind pose |
| Copy Left → Paste Right | Mirror selected bone(s) left to right |
| Copy Right → Paste Left | Mirror selected bone(s) right to left |
| 🚀 BUILD STANDARD RIG | Build Max Bones from the loaded profile |
| 🎬 Open Batch Retargeter | Open the retargeting window |
| ℹ️ About / Settings | Version info, GitHub link, donation link |

### Batch Retargeter

| Control | Function |
|---------|----------|
| 📂 Import Data (FBX/BVH) | Import motion file. Cleans up previous import first |
| Insert Ref Frame | Shift all keys +1 frame and create a clean T-pose at frame 0 |
| 🙆 Fix Arms | Rotate arm bones +85° / -85° around the bone forward axis |
| 📏 Auto-Scale | Scale source skeleton to match target rig height |
| 🦴 Visual Skeleton | Draw yellow lines along source skeleton |
| ✨ Auto-Guess | Auto-fill the mapping table using pattern matching |
| 💾 Save Map | Save the current mapping to a JSON file |
| 📂 Load Map | Load a previously saved mapping |
| Transfer Root Position | Also constrain hip position (not just rotation) |
| 🔗 LINK RIG (Fixed Orient) | Apply Orientation Constraints from source to target |

### Mapping Editor

| Column | Description |
|--------|-------------|
| Alias | Internal name for this bone entry |
| Bone Suffix | Name of the built Max Bone |
| Param Name | Skin modifier bone lookup name |
| FBX Pattern | Substring matched against FBX bone names for Skin transfer |
| Mode | `PR` = Position+Rotation SNAP · `R` = Rotation only · `D` = Delta/matrix |
| Transform Matrix | 4×3 rotation correction matrix (rows = X, Y, Z axes + translation) |
| Status | `OK` (bone found in scene) or `MISSING` |

---

## JSON Profile Format

Profiles live in `JSON/Profile/`. Each file describes one rig type.

```json
{
    "profile_name": "Mixamo_To_Standard",
    "rig_name": "__MIXAMO__",
    "scale_factor": 1.0,
    "mapping": {
        "Hips": {
            "target_bone": "Pelvis",
            "param_name": "Pelvis",
            "pattern": "Hips",
            "mode": "PR",
            "method": "SNAP",
            "matrix": [[0,1,0], [0,0,1], [1,0,0], [0,0,0]]
        }
    }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `profile_name` | string | Human-readable name |
| `rig_name` | string | Name of the Dummy root created in the scene |
| `scale_factor` | float | Global scale override (usually `1.0`) |
| `mapping` | object | Dict of bone entries keyed by alias |

### Per-Bone Entry

| Field | Type | Description |
|-------|------|-------------|
| `target_bone` | string | Name of the Max Bone to create |
| `param_name` | string | Name used in Skin modifier |
| `pattern` | string | Substring for matching FBX source bones during Skin transfer |
| `mode` | `PR` / `R` / `D` | How the bone is placed: Position+Rotation, Rotation only, or Delta |
| `matrix` | 4×3 array | Rotation correction matrix. Row 1-3 = X/Y/Z axes, Row 4 = translation offset |

### Matrix Format

```json
"matrix": [
    [Xx, Xy, Xz],
    [Yx, Yy, Yz],
    [Zx, Zy, Zz],
    [Tx, Ty, Tz]
]
```

Identity (no correction): `[[1,0,0],[0,1,0],[0,0,1],[0,0,0]]`

---

## Retarget Map Format

Saved mapping files (`JSON/Retargetmap/`) store the alias → source bone assignments:

```json
{
    "Hips": "BVH_Hips",
    "Spine": "BVH_Spine",
    "LeftArm": "BVH_LeftArm"
}
```

---

## How Retargeting Works

MAXRIG PRO uses a **ghost helper + Orientation Constraint** approach:

1. At frame 0 (bind pose), a `GHOST_ROT_{alias}` Point helper is created.
2. The ghost is parented to the **source bone** and given a local rotation equal to:
   ```
   correction = normalize(R_target_bind) × inv(normalize(R_source_bind))
   ```
3. An **Orientation Constraint** (`relative=false`) drives the target bone to match the ghost's world rotation.
4. As the source animates, the ghost's world rotation = `correction × R_source_current`, which maps the source animation into the target's coordinate space.

For **FBX** (`ANIM_` prefix): The bind pose is read from the original static character bone (same name without `ANIM_`), not the animated import.

For **root position**: A `GHOST_POS_{alias}` helper with a Position Constraint offsets the target hips by the world-space delta between bind poses.

---

## Mirror Bones

Uses a **delta-from-bind-pose** formula to correctly handle both T-pose and A-pose rigs:

1. `delta = inv(src_bind_rot) × src_current_rot`
2. Mirror delta across the YZ plane
3. `result = dst_bind_rot × mirrored_delta`

The bind pose snapshot is captured automatically when:
- The rig is built (BUILD STANDARD RIG)
- The Skin modifier is toggled (Lock/Unlock)
- A JSON profile is loaded

---

## File Structure

```
MAXRIGPRO/
├── core.py          # Main UI (AutoRIGG_UI) + BatchRetargeter logic
├── dialogs.py       # MappingEditor, LiveCalibrator, ValidationReportDialog, AboutDialog
├── utils.py         # SimpleBVHImporter, BVH axis conversion
├── widgets.py       # QLogger (thread-safe log widget)
├── constants.py     # Version, URLs, layer names, colors
├── Cat_core.py      # CAT rig builder (optional)
└── maxrigpro.py     # Entry point: launch_maxrig_pro()

JSON/
├── Profile/         # Rig profiles (Mixamo, ACCURIG, Cascadur, Rokoko)
└── Retargetmap/     # Saved bone mapping files
```

---

## Workflow Recipes

### Mixamo FBX → Standard Rig

```
1. File > Import > Merge Mixamo character FBX
2. Load Configuration → Profile_Mixamo.json
3. BUILD STANDARD RIG
4. Open Batch Retargeter
5. Import Data → any Mixamo animation FBX
6. Auto-Guess → LINK RIG
```

### CMU / Rokoko BVH → Cascadur Rig

```
1. Import Cascadur character FBX
2. Load Configuration → Profile_Cascadur.json
3. BUILD STANDARD RIG
4. Open Batch Retargeter
5. Import Data → BVH file
6. Insert Ref Frame (creates T-pose at frame 0)
7. Fix Arms (if A-pose source)
8. Auto-Scale
9. Auto-Guess → LINK RIG
```

### Fix Bone Alignment After Build

```
1. UNLOCK BONES (Disable Skin)
2. Move / Rotate bones in viewport
3. Use Mirror Bones to sync left ↔ right
4. LOCK BONES (Re-enable Skin) → bind pose is updated
```

---

## Known Limitations

- CAT rig builder (`Cat_core.py`) is experimental.
- Finger retargeting requires the source motion to have finger data.
- `Fix Arms` rotates by a fixed ±85° — manual adjustment may be needed for non-standard A-pose angles.
- BVH files with non-standard hierarchy (no single root) may need manual mapping.

---

## License

MIT License — free to use and modify. If you find it useful, consider supporting development:

[![Donate](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/donate/?hosted_button_id=LAMNRY6DDWDC4)

---

## Contributing

Pull requests and issues are welcome at [github.com/imanshirani/MAXRIGPRO](https://github.com/imanshirani/MAXRIGPRO/).

When adding a new profile JSON, follow the existing format and test with at least one BVH and one FBX animation file.



