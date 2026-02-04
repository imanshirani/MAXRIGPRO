# 🚀 MAXRIG PRO (Beta)
**Advanced Auto-Rigging & Animation Retargeting Suite for 3ds Max**

MAXRIG PRO is a modular Python-based toolset designed to bridge the gap between custom FBX/BVH motion data and standard 3ds Max bone systems. It automates rig building, skin transfer, and complex animation retargeting through a data-driven JSON pipeline.

---

## ✨ Key Features
* **Automated Rig Builder:** Generate clean, standard bone hierarchies from JSON configurations.
* **Intelligent Skin Transfer:** Robustly re-assign skin weights from source meshes to the new standard rig.
* **Universal Retargeter:** Batch process FBX and BVH motion data with "Auto-Guess" bone mapping.
* **Live Calibrator:** A visual helper tool to align bone orientations using 3D "Ghost" helpers.
* **Modular Architecture:** Easily extendable codebase using PySide6 and pymxs.

## 🛠 Installation & Launch
1. Clone this repository into your 3ds Max scripts folder.
2. In 3ds Max, go to **Scripting -> Python 3.x Script...**
3. Select and run `launch.py`.
4. The tool will appear as a dockable QDockWidget for easy access.

## ⚠️ Beta Note (Known Issues)
* **FBX Rotation Inconsistencies:** Some FBX files may require manual adjustment via the **Live Calibrator** due to varied coordinate systems.
* **Undo History:** Large skin transfer operations might take a moment to register in the undo buffer.
