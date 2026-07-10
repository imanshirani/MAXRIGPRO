import json
import fnmatch
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                               QMessageBox, QGroupBox, QDialog, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QTextEdit, 
                               QLineEdit, QCheckBox, QFileDialog, QAbstractItemView, 
                               QGridLayout)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
import pymxs
rt = pymxs.runtime


import constants 
from utils import QLogger, SimpleBVHImporter, open_url 
from widgets import MatrixCellWidget
from dialogs import MappingEditor, LiveCalibrator, ValidationReportDialog
# ---------------------------------------------------------------------------
# 2. MAIN APP
# ---------------------------------------------------------------------------
class AutoRIGG_UI(QWidget):
    def __init__(self):
        super(AutoRIGG_UI, self).__init__()
        self.setWindowTitle("Auto-Rig Builder (Standard Max Bones)")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint) 
        self.resize(400, 500)
        
        self.logger = QLogger()
        self.logger.sig_log.connect(self.append_log)
        
        self.full_json_data = {}
        self.current_mapping = {}
        self.bind_pose_snapshot = {}  # {node_name: transform} captured on skin-disable

        self.init_ui()
        self.logger.info(f"--- {constants.PRODUCT_NAME} v{constants.VERSION} Loaded ---", constants.LOGGER_INFO_COLOR)
        
    def init_ui(self):
        layout = QVBoxLayout()       
        
        
        # --- Group 0: Product Info & Settings ---
        grp_info = QGroupBox("System && Info")
        l_info = QHBoxLayout()
        
        title_lbl = QLabel(f"<b>{constants.PRODUCT_NAME}</b> {constants.VERSION}")
        title_lbl.setStyleSheet("color: #00AAFF;")
        
        btn_about = QPushButton("ℹ️ About / Settings")
        btn_about.setFixedSize(120, 30)
        btn_about.clicked.connect(self.show_about_dialog)
        
        l_info.addWidget(title_lbl)
        l_info.addStretch()
        l_info.addWidget(btn_about)
        
        grp_info.setLayout(l_info)
        layout.addWidget(grp_info)

        
        

        # --- BONE PLACEMENT FIXER (SKIN TOGGLE) <<<
        grp_fix = QGroupBox("Bone Placement")
        l_fix = QVBoxLayout()
        
        
        lbl_info = QLabel("Use this if bones are not aligned with mesh volume.\n(e.g. Elbow bone is outside the mesh arm)")
        lbl_info.setStyleSheet("color: #AAA; font-size: 10px; font-style: italic;")
        l_fix.addWidget(lbl_info)
        
        #(Toggle)
        self.btn_unlock = QPushButton("🔓 UNLOCK BONES (Disable Skin)")
        self.btn_unlock.setCheckable(True)
        self.btn_unlock.setFixedHeight(40)
        self.btn_unlock.setStyleSheet("""
            
            QPushButton:checked { background-color: #AA2222; color: white; border: 2px solid #FF5555; }
        """)
        self.btn_unlock.toggled.connect(self.toggle_skin_mode)
        l_fix.addWidget(self.btn_unlock)
        
        
        self.lbl_mode_status = QLabel("State: Locked (Safe)")
        self.lbl_mode_status.setAlignment(Qt.AlignCenter)
        l_fix.addWidget(self.lbl_mode_status)

        grp_fix.setLayout(l_fix)
        layout.addWidget(grp_fix)


        # --- Group 00. POSE CORRECTION (T-POSE) <<<
        grp_mirror = QGroupBox("Mirror Selected Bones")
        l_mirror = QVBoxLayout()
        
        lbl_hint = QLabel(
            "1. Select the bone(s) you fixed manually.\n"
            "2. Click 'Paste Mirror' to apply to the other side.\n"
            "(Works on Selection Only)")        
        l_mirror.addWidget(lbl_hint)
        
        
        hbox_btns = QHBoxLayout()
        
        # L -> R
        btn_l2r = QPushButton("Copy Left -> Paste Right")
        btn_l2r.setFixedHeight(40)
        btn_l2r.clicked.connect(lambda: self.mirror_selection_logic("left_to_right"))
        
        # R -> L
        btn_r2l = QPushButton("Copy Right -> Paste Left")
        btn_r2l.setFixedHeight(40)
        btn_r2l.clicked.connect(lambda: self.mirror_selection_logic("right_to_left"))
        
        hbox_btns.addWidget(btn_l2r)
        hbox_btns.addWidget(btn_r2l)
        l_mirror.addLayout(hbox_btns)

        grp_mirror.setLayout(l_mirror)
        layout.addWidget(grp_mirror)

        # --- Group 1: Configuration ---
        grp_config = QGroupBox("Setup && Mapping")
        l_config = QVBoxLayout()
        
        
        btn_load = QPushButton("📂 Load Configuration (JSON)")
        btn_load.setFixedHeight(35)
        btn_load.clicked.connect(self.load_json_file)
        l_config.addWidget(btn_load)
        
        
        btn_edit = QPushButton("✏️ Edit Mapping / Bone Names")
        btn_edit.setFixedHeight(35)
        btn_edit.clicked.connect(self.open_mapping_editor)
        l_config.addWidget(btn_edit)
        
        grp_config.setLayout(l_config)
        layout.addWidget(grp_config)
        
        # --- Group 2: Tools ---
        grp_tools = QGroupBox("Visual Tools")
        l_tools = QVBoxLayout()
        
        self.chk_debug = QCheckBox("Show Debug Helpers (Red Points)")
        l_tools.addWidget(self.chk_debug)

        btn_ghost = QPushButton("👻 Create Ghosts (Check Alignment)")
        btn_ghost.clicked.connect(self.create_ghost_helpers)
        l_tools.addWidget(btn_ghost)
        
        grp_tools.setLayout(l_tools)
        layout.addWidget(grp_tools)

        # --- Group 3: Build ---
        grp_run = QGroupBox("Execution")
        l_run = QVBoxLayout()

        self.btn_run = QPushButton("🚀 BUILD STANDARD RIG")
        self.btn_run.setFixedHeight(50)
        self.btn_run.clicked.connect(self.run_process)
        l_run.addWidget(self.btn_run)

        grp_run.setLayout(l_run)
        layout.addWidget(grp_run)

        # --- Group 4: RETARGETING (NEW) ---
        grp_retarget = QGroupBox("Animation Retargeting")
        l_ret = QVBoxLayout()
        
        btn_batch = QPushButton("🎬 Open Batch Retargeter")
        btn_batch.setFixedHeight(40)
        btn_batch.clicked.connect(self.open_batch_retargeter)
        l_ret.addWidget(btn_batch)
        
        grp_retarget.setLayout(l_ret)
        layout.addWidget(grp_retarget)
        
        # --- Log ---
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #222; color: #8F8; font-family: Consolas; font-size: 11px;")
        layout.addWidget(self.log_text)

        self.setLayout(layout)

    def open_batch_retargeter(self):
        if not hasattr(self, 'retarget_win') or not self.retarget_win.isVisible():
            self.retarget_win = BatchRetargeter(self)
        self.retarget_win.show()

    def open_calibrator(self):
        self.calib_win = LiveCalibrator(self)
        self.calib_win.show()

    def load_json_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Master JSON", "", "JSON Files (*.json)")
        if not path: return
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            self.full_json_data = data
            self.current_mapping = data.get("mapping", {})
            
            
            rig_name = data.get("rig_name", "Unknown")
            count = len(self.current_mapping)
            
            self.logger.info(f"JSON Loaded.Loaded: {os.path.basename(path)} | Target Rig Name: '{rig_name}'| Bones: {count}")
            self._capture_bind_pose_snapshot()

        except Exception as e:
            self.logger.error(f"JSON Error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load JSON:\n{e}")



    def append_log(self, msg, color):
        self.log_text.append(f'<span style="color:{color}">{msg}</span>')

    def show_about_dialog(self):
        from dialogs import AboutDialog #
        dlg = AboutDialog(self)
        dlg.exec_()

    def open_mapping_editor(self, target_alias=None):
        
        if not self.full_json_data:
            self.full_json_data = {
                "profile_name": "New_Profile",
                "rig_name": "Base Human", 
                "scale_factor": 1.0,
                "mapping": {}
            }
        
        
        if hasattr(self, "editor_win") and self.editor_win.isVisible():
            self.editor_win.raise_()
            if target_alias: self.editor_win.highlight_row(target_alias)
            return

        
        self.editor_win = MappingEditor(self.full_json_data, self)       
        
        self.editor_win.setWindowModality(Qt.NonModal)

        
        def sync_data(result):
            if result == QDialog.Accepted: 
                self.full_json_data = self.editor_win.get_full_json_data()
                self.current_mapping = self.full_json_data["mapping"]
                count = len(self.current_mapping)
                self.logger.info(f"Mapping applied/updated. Bones: {count}")

        self.editor_win.finished.connect(sync_data)

        
        if target_alias:
            self.editor_win.highlight_row(target_alias)

        
        self.editor_win.show()

    def save_current_json(self):
        if not self.full_json_data:
            self.logger.warning("Nothing to save.")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Save JSON", "", "JSON Files (*.json)")
        if path:
            try:
                
                self.full_json_data["mapping"] = self.current_mapping
                with open(path, 'w') as f:
                    json.dump(self.full_json_data, f, indent=4)
                self.logger.info(f"Saved to {path}")
            except Exception as e:
                self.logger.error(f"Save Error: {e}")

    # -----------------------------------------------------------------------
    # LOGIC UTILS
    # -----------------------------------------------------------------------
    def toggle_skin_mode(self, checked):
        state_bool = "false" if checked else "true"
        
        if checked:
            self.lbl_mode_status.setText("State: ⚠️ EDIT MODE (Skin Disabled)")
            self.lbl_mode_status.setStyleSheet("color: #FF5555; font-weight: bold;")
            self.btn_unlock.setText("🔒 LOCK BONES (Apply Fix)")
            self.logger.info("Skin DISABLED. Adjust bones now.")
            # Snapshot current transforms as the bind pose reference for mirror
            self._capture_bind_pose_snapshot()
        else:
            self.lbl_mode_status.setText("State: Locked (Safe)")
            self.lbl_mode_status.setStyleSheet("color: #00FF00;")
            self.btn_unlock.setText("🔓 UNLOCK BONES (Edit Placement)")
            self.logger.info("Skin ENABLED. Bind Pose Updated.")
            # Update snapshot so next edit session starts from the new bind pose
            self._capture_bind_pose_snapshot()

        
        mxs_script = f"""
        (
            local meshes = for o in objects where (isValidNode o and o.modifiers[#Skin]!=undefined) collect o
            
            for m in meshes do (
                local skinMod = m.modifiers[#Skin]
                
                
                skinMod.enabled = {state_bool}
                
                if ({state_bool} == true) do (
                    
                    select m
                    max modify mode
                    modPanel.setCurrentObject skinMod
                    
                    
                    skinMod.always_deform = false
                    
                    
                    redrawViews() 
                    
                    skinMod.always_deform = true
                )
            )
            clearSelection()
        )
        """
        try:
            rt.execute(mxs_script)
        except Exception as e:
            self.logger.error(f"Skin Toggle Error: {e}")

    def _capture_bind_pose_snapshot(self):
        """Store world transforms of all scene objects as bind pose reference for mirror."""
        self.bind_pose_snapshot = {}
        for obj in rt.objects:
            if rt.isValidNode(obj):
                tm = obj.transform
                self.bind_pose_snapshot[obj.name] = rt.matrix3(
                    tm.row1, tm.row2, tm.row3, tm.row4
                )
        self.logger.info(f"Bind pose snapshot: {len(self.bind_pose_snapshot)} objects captured.")

    def mirror_selection_logic(self, direction):
        """
        Mirror across the YZ plane (flip X axis).
        Formula: dst.transform = mirror_tm * src.transform * mirror_tm
        where mirror_tm = scaleMatrix([-1, 1, 1])
        """
        if not self.current_mapping:
            self.logger.warning("Load JSON first.")
            return

        selection = list(rt.selection)
        if not selection:
            self.logger.warning("Select bone(s) first!")
            return

        # Flip X axis — mirrors position and rotation axes across the YZ plane.
        mirror_tm = rt.scaleMatrix(rt.point3(-1, 1, 1))

        # Auto-capture bind pose if not captured yet
        if not self.bind_pose_snapshot:
            self._capture_bind_pose_snapshot()

        self.logger.info(f"Mirroring Selection ({direction})...")
        bone_pairs = self.build_bone_pairs_from_scene()

        count = 0
        with pymxs.undo(True), pymxs.animate(False):
            for src_node in selection:
                pair_data = self.find_pair_in_dict(src_node, bone_pairs)
                if not pair_data: continue

                if direction == "left_to_right" and pair_data['side'] != 'left': continue
                if direction == "right_to_left" and pair_data['side'] != 'right': continue

                dst_node = pair_data['other_node']
                if not dst_node: continue

                try:
                    src_name = src_node.name
                    dst_name = dst_node.name

                    src_bind = self.bind_pose_snapshot.get(src_name)
                    dst_bind = self.bind_pose_snapshot.get(dst_name)
                    self.logger.info(f"[MIRROR] {src_name}->{dst_name} | snapshot_src={'YES' if src_bind else 'NO'} snapshot_dst={'YES' if dst_bind else 'NO'}")

                    if src_bind and dst_bind:
                        # Delta-from-bind approach (works for any pose including A-pose):
                        # 1. delta_rot = inv(src_bind_rot) * src_current_rot
                        # 2. mirror delta across YZ: negate X col of each row
                        # 3. dst_result = dst_bind_rot * mirrored_delta
                        src_bind_rot = rt.matrix3(src_bind.row1, src_bind.row2, src_bind.row3, rt.point3(0,0,0))
                        dst_bind_rot = rt.matrix3(dst_bind.row1, dst_bind.row2, dst_bind.row3, rt.point3(0,0,0))
                        src_cur_rot  = rt.matrix3(src_node.transform.row1, src_node.transform.row2, src_node.transform.row3, rt.point3(0,0,0))

                        delta = rt.inverse(src_bind_rot) * src_cur_rot

                        # Mirror the delta: negate X component of each column
                        # (reflect across local YZ = negate col 1 of matrix)
                        d1 = delta.row1; d2 = delta.row2; d3 = delta.row3
                        mir_delta = rt.matrix3(
                            rt.point3( d1.x, -d1.y, -d1.z),
                            rt.point3(-d2.x,  d2.y,  d2.z),
                            rt.point3(-d3.x,  d3.y,  d3.z),
                            rt.point3(0, 0, 0)
                        )

                        result_rot = dst_bind_rot * mir_delta
                        dst_node.transform = rt.matrix3(
                            result_rot.row1, result_rot.row2, result_rot.row3,
                            dst_node.pos
                        )
                        self.logger.info(f"Mirrored (delta): {src_name} -> {dst_name}")
                    else:
                        # Fallback: no snapshot yet — direct YZ mirror
                        s = src_node.transform
                        mirror_tm = rt.scaleMatrix(rt.point3(-1, 1, 1))
                        mirrored = mirror_tm * s * mirror_tm
                        dst_node.transform = rt.matrix3(mirrored.row1, mirrored.row2, mirrored.row3, dst_node.pos)
                        self.logger.info(f"Mirrored (direct): {src_name} -> {dst_name}")
                    count += 1
                except Exception as e:
                    self.logger.error(f"Err {src_node.name}: {e}")

        if count > 0:
            rt.redrawViews()
            self.logger.info(f"Success! Mirrored {count} bones.")
        else:
            self.logger.warning("No valid pairs found.")

    def build_bone_pairs_from_scene(self):
        """
        Build a lookup of {scene_node: {side, other_node}} for all L/R pairs.
        Registers both the FBX source node (via resolve_fbx_node) and the built
        target bone (via getNodeByName on target_bone) so the user can select
        either and mirror will find the pair.
        """
        base_map = {}

        def detect_side(name):
            """Return (side, base) for any common L/R naming convention, or (None, None)."""
            n = name.lower()
            # suffix: _l / _r  (e.g. index1_l, armtwistL → lower = armtwistl)
            if n.endswith("_l"):
                return 'left',  name[:-2]
            if n.endswith("_r"):
                return 'right', name[:-2]
            # camelCase suffix: ...L / ...R (e.g. armtwistL, weaponL)
            if len(name) > 1 and name[-1] == 'L' and name[-2].islower():
                return 'left',  name[:-1]
            if len(name) > 1 and name[-1] == 'R' and name[-2].islower():
                return 'right', name[:-1]
            # prefix: L.../R... but not "Lower", "Root", "Ribcage"
            SKIP_L = ("lower", "line")
            SKIP_R = ("root", "ribcage", "right")
            if n.startswith("l") and not any(n.startswith(s) for s in SKIP_L):
                return 'left',  name[1:]
            if n.startswith("r") and not any(n.startswith(s) for s in SKIP_R):
                return 'right', name[1:]
            # word: Left.../Right...
            if "left" in n:
                return 'left',  name.replace("Left","").replace("left","")
            if "right" in n:
                return 'right', name.replace("Right","").replace("right","")
            return None, None

        for alias, props in self.current_mapping.items():
            t_name = props.get("target_bone", alias)
            side, base = detect_side(t_name)

            if side and base:
                if base not in base_map: base_map[base] = {}
                base_map[base][side] = props

        final_lookup = {}

        for base, sides in base_map.items():
            if 'left' not in sides or 'right' not in sides: continue

            l_props, r_props = sides['left'], sides['right']

            # Collect candidate nodes for each side: FBX source + built target bone
            def get_nodes(p):
                nodes = []
                fbx = self.resolve_fbx_node(p)
                if fbx: nodes.append(fbx)
                tgt = rt.getNodeByName(p.get("target_bone", ""))
                if tgt and rt.isValidNode(tgt): nodes.append(tgt)
                return nodes

            l_nodes = get_nodes(l_props)
            r_nodes = get_nodes(r_props)

            for l_node in l_nodes:
                # Prefer the matching type (FBX↔FBX or bone↔bone); fall back to first available
                r_match = next((n for n in r_nodes if type(n) == type(l_node)), r_nodes[0] if r_nodes else None)
                if r_match:
                    final_lookup[l_node] = {'side': 'left',  'other_node': r_match}
            for r_node in r_nodes:
                l_match = next((n for n in l_nodes if type(n) == type(r_node)), l_nodes[0] if l_nodes else None)
                if l_match:
                    final_lookup[r_node] = {'side': 'right', 'other_node': l_match}

        return final_lookup

    def find_pair_in_dict(self, node, lookup_dict):
        
        for k, v in lookup_dict.items():
            if k == node: return v
        return None
    
    
    
    def resolve_fbx_node(self, data):
        pattern = data
        if isinstance(data, dict): pattern = data.get("pattern", "")
        if not pattern: return None
        
        exact = rt.getNodeByName(pattern)
        if exact: return exact
        
        import fnmatch
        for o in rt.objects:
            if fnmatch.fnmatch(o.name, pattern): return o
        return None

    def get_correction_matrix(self, map_data):
        
        mat = rt.matrix3(1)
        
        raw_mtx = map_data.get("matrix", [])
        
        
        if isinstance(raw_mtx, list) and len(raw_mtx) >= 3:
            try:
                r1 = rt.point3(raw_mtx[0][0], raw_mtx[0][1], raw_mtx[0][2])
                r2 = rt.point3(raw_mtx[1][0], raw_mtx[1][1], raw_mtx[1][2])
                r3 = rt.point3(raw_mtx[2][0], raw_mtx[2][1], raw_mtx[2][2])
                
                
                r4 = rt.point3(0,0,0)
                if len(raw_mtx) == 4:
                    r4 = rt.point3(raw_mtx[3][0], raw_mtx[3][1], raw_mtx[3][2])
                
                mat = rt.matrix3(r1, r2, r3, r4)
            except Exception as e:
                
                print(f"Matrix Parse Error for {map_data.get('target_bone')}: {e}")
                
        return mat

    def get_lookat_matrix(self, dir_vec):
        up_vec = rt.point3(0,0,1)
        x_axis = rt.normalize(dir_vec)
        if abs(rt.dot(x_axis, up_vec)) > 0.99:
            z_axis = rt.normalize(rt.cross(x_axis, rt.point3(0,1,0)))
        else:
            z_axis = rt.normalize(rt.cross(x_axis, up_vec))
        y_axis = rt.normalize(rt.cross(x_axis, z_axis))
        return rt.matrix3(x_axis, y_axis, z_axis, rt.point3(0,0,0))

    # -----------------------------------------------------------------------
    # FIND Find bone fuzzy
    # -----------------------------------------------------------------------

    def find_bone_fuzzy(self, rig_prefix, suffix_hint):
        
        if not suffix_hint: return None
        
        candidates = [
            f"{rig_prefix} {suffix_hint}", 
            f"{rig_prefix}{suffix_hint}",  
            suffix_hint                    
        ]
        
        for name in candidates:
            node = rt.getNodeByName(name)
            if node: return node
            
            res = rt.execute(f'GetNodeByName "{name}" ignoreCase:true')
            if res: return res
            
        return None   
    
    

    
    # --- T-Pose ---
    def reset_source_pose(self):
        
        self.logger.info("Step 0: Resetting Source T-Pose...")
        for alias, props in self.current_mapping.items():
            src_node = self.resolve_fbx_node(props)
            if src_node:
                with pymxs.animate(False):
                   
                    src_node.rotation = rt.quat(0,0,0,1) 
        rt.completeRedraw()
    
    

    
    # AutoRIGG_UI 
    def connect_animation_source(self):
        self.logger.info("--- Connecting Animation Source ---")
        
        
        
        with pymxs.undo(True), pymxs.animate(False):
            for alias, props in self.current_mapping.items():
                target_name = props.get("target_bone", alias)
                
                
                std_bone = rt.getNodeByName(target_name)
                
                
                src_node = self.resolve_fbx_node(props) 
                
                if std_bone and src_node:                  
                    
                    
                    std_bone.rotation.controller = rt.TCB_Rotation() 
                    
                    constraint = rt.Orientation_Constraint()
                    std_bone.rotation.controller = constraint
                    
                    
                    constraint.appendTarget(src_node, 100.0)
                    
                    
                    constraint.relative = True 
                    
                    self.logger.info(f"Linked: {std_bone.name} <--- {src_node.name}")
                    
        self.logger.info("Animation Linked! logic complete.")

    def get_stable_lookat_matrix(self, start_pos, target_pos, source_transform_up_hint):        
        dir_vector = target_pos - start_pos
        length = rt.length(dir_vector)
        if length < 0.001: return rt.matrix3(1) 
        
        x_axis = rt.normalize(dir_vector)
        
        
        up_hint = rt.normalize(source_transform_up_hint)
        
        
        if abs(rt.dot(x_axis, up_hint)) > 0.98:
            up_hint = rt.point3(0, 0, 1) 
            
        
        z_axis = rt.normalize(rt.cross(x_axis, up_hint)) 
        y_axis = rt.normalize(rt.cross(z_axis, x_axis))  
        
        
        
        return rt.matrix3(x_axis, y_axis, z_axis, start_pos)
    
      
    def get_mapped_child(self, source_node):
        if not source_node: return None
        import fnmatch
        for child in source_node.children:
            for alias, props in self.current_mapping.items():
                pattern = props.get("pattern", "")
                if fnmatch.fnmatch(child.name, pattern):
                    return child
        if source_node.children.count > 0:
            return source_node.children[0]
        return None

    # -----------------------------------------------------------------------
    # NEW: AUTO-VALIDATOR LOGIC
    # -----------------------------------------------------------------------
    def validate_and_run(self):
        
        loop_count = 0
        max_loops = 3 
        
        while True:
            if loop_count >= max_loops:
                self.logger.warning("Validation stopped to prevent infinite loop. Please check remaining issues manually.")
                break
                
            self.logger.info(f"Running Exact Math Validation (Pass {loop_count + 1})...")
            
            if not self.current_mapping:
                self.logger.error("No mapping loaded!")
                return

            errors = []
            
            
            def clean_val(n):
                
                if abs(n - round(n)) < 0.001: return int(round(n))
                return float(round(n, 4))

            def matrix_to_json_list(tm):
                
                r1 = [clean_val(tm.row1.x), clean_val(tm.row1.y), clean_val(tm.row1.z)]
                r2 = [clean_val(tm.row2.x), clean_val(tm.row2.y), clean_val(tm.row2.z)]
                r3 = [clean_val(tm.row3.x), clean_val(tm.row3.y), clean_val(tm.row3.z)]
                r4 = [0, 0, 0] 
                return [r1, r2, r3, r4]

            def format_disp(lst):
                return f"[{lst[0]}, {lst[1]}, {lst[2]}]"

            for alias, props in self.current_mapping.items():
                mode = props.get("mode", "PR").upper()
                
                
                if "D" in mode:
                    src_node = self.resolve_fbx_node(props)
                    child_node = self.get_mapped_child(src_node)
                    
                    if src_node and child_node:
                        
                        vec_real = rt.normalize(child_node.pos - src_node.pos)
                        
                        
                        correction_tm = self.get_correction_matrix(props)
                        current_result_tm = src_node.transform * correction_tm
                        
                        
                        vec_current = rt.normalize(current_result_tm.row1) 
                        
                        
                        if rt.dot(vec_real, vec_current) < 0.99:
                            
                            
                            ideal_x = vec_real
                            
                            
                            up_hint = rt.normalize(src_node.transform.row3)
                            
                            
                            if abs(rt.dot(ideal_x, up_hint)) > 0.95:
                                up_hint = rt.point3(0,0,1)
                                
                            ideal_z = rt.normalize(rt.cross(ideal_x, up_hint))
                            ideal_y = rt.normalize(rt.cross(ideal_z, ideal_x))
                            
                            
                            ideal_tm = rt.matrix3(ideal_x, ideal_y, ideal_z, src_node.pos)
                            
                            
                            
                            needed_correction = rt.inverse(src_node.transform) * ideal_tm
                            
                            
                            new_matrix_data = matrix_to_json_list(needed_correction)
                            
                            
                            current_json_str = json.dumps(props.get("matrix", []))
                            new_json_str = json.dumps(new_matrix_data)
                            
                            if current_json_str != new_json_str:
                                disp_str = format_disp(new_matrix_data)
                                errors.append({
                                    "alias": alias, 
                                    "msg": "Misaligned", 
                                    "fix_text": f"Calculated Solution:\n{disp_str}",
                                    "fix_data": new_matrix_data 
                                })

            
            if errors:
                dlg = ValidationReportDialog(errors, self)
                dlg.exec()
                
                if dlg.action == "auto_fix":
                    loop_count += 1
                    self.logger.info("Applying Calculated Math Fixes...")
                    
                    count = 0
                    for err in errors:
                        alias = err['alias']
                        new_data = err['fix_data']
                        
                        if alias in self.current_mapping:
                            self.current_mapping[alias]["matrix"] = new_data
                            count += 1
                            
                    
                    self.full_json_data["mapping"] = self.current_mapping
                    
                    continue 

                elif dlg.action == "manual_fix" and dlg.selected_alias:
                    self.open_mapping_editor(dlg.selected_alias)
                    continue
                    
                elif dlg.action == "build":
                    self.run_process()
                    break
                else:
                    self.logger.info("Cancelled.")
                    break
            else:
                self.logger.info("Validation Passed ✅. Exact match found. Building Rig...")
                self.run_process()
                break

    def create_ghost_helpers(self):
        
        if not self.current_mapping: 
            QMessageBox.warning(self, "Error", "Please Load JSON first.")
            return

        # Ghost
        layer_name = "AUTO_CAT_GHOSTS"
        if not rt.LayerManager.getLayerFromName(layer_name):
            rt.LayerManager.newLayerFromName(layer_name)
        layer = rt.LayerManager.getLayerFromName(layer_name)
        layer.current = True

        count = 0
        
        
        rt.suspendEditing()

        for alias, props in self.current_mapping.items():
            src_node = self.resolve_fbx_node(props)
            
            if src_node:
                
                ghost_name = f"GHOST_{alias}"
                old = rt.getNodeByName(ghost_name)
                if old: rt.delete(old)

                
                p = rt.Point(pos=src_node.pos, size=4.0, axis=True, wirecolor=rt.color(255, 0, 255))
                p.name = ghost_name
                
                
                p.transform = src_node.transform
                
                count += 1
                
                
                if self.chk_debug.isChecked():
                    red_name = f"DEBUG_RED_{alias}"
                    old_red = rt.getNodeByName(red_name)
                    if old_red: rt.delete(old_red)
                    
                    p_red = rt.Point(pos=src_node.pos, size=2.0, wirecolor=rt.color(255, 0, 0), axis=True)
                    p_red.transform = src_node.transform
                    p_red.name = red_name
                    
                    rt.setUserProp(p_red, "TargetAlias", alias)

        rt.resumeEditing()
        rt.completeRedraw()
        
        if count == 0:
            self.logger.warning("No source bones found! Check pattern names in JSON.")
        else:
            self.logger.info(f"Created {count} Ghosts exactly on FBX bones.")
            self.logger.info("NOW: Rotate Pink Points manually -> Then click BUILD.")            
    
    
    
    def get_json_pos_by_target_bone(self, target_suffix):
        """
        Search the current mapping to find the Position [x,y,z] 
        associated with a specific CAT bone suffix (e.g. 'LCalf').
        Returns pymxs.runtime.Point3 or None.
        """
        for alias, data in self.current_mapping.items():
            # Check if this mapping entry corresponds to the target suffix
            if data.get("target_bone") == target_suffix:
                mat_data = data.get("matrix", [])
                if len(mat_data) >= 4:
                    # Row 4 is Position
                    row4 = mat_data[3]
                    return rt.Point3(row4[0], row4[1], row4[2])
        return None

    
    
    def find_nearest_mapped_ancestor(self, src_node, created_bones_map):
        
        current = src_node.parent
        while current:
            if current in created_bones_map:
                return created_bones_map[current]
            current = current.parent
        return None
    
    
    # -----------------------------------------------------------------------
    # SKIN TRANSFER ENGINE
    # -----------------------------------------------------------------------
    def transfer_skin_to_standard_rig(self):
        self.logger.info("--- Phase 3: Skin Transfer ---")

        skinned_meshes = [o for o in rt.objects if rt.isValidNode(o) and o.modifiers[rt.name("Skin")] is not None]
        if not skinned_meshes: return

        count = 0
        rt.suspendEditing()

        try:
            for mesh_obj in skinned_meshes:
                rt.select(mesh_obj)
                rt.execute("max modify mode")

                skin_mod = mesh_obj.modifiers[rt.name("Skin")]
                rt.modPanel.setCurrentObject(skin_mod)

                num_bones = rt.skinOps.GetNumberBones(skin_mod)

                # Collect replacements first so that ReplaceBone index-shifts don't
                # corrupt subsequent lookups.  Process high→low index after collection.
                # Sort mapping by pattern specificity (longest clean_pattern first) so that
                # "mixamorig:LeftHandIndex1" matches before the shorter "mixamorig:LeftHand".
                sorted_mapping = sorted(
                    self.current_mapping.items(),
                    key=lambda kv: len(kv[1].get("pattern", "").replace("*", "")),
                    reverse=True
                )
                replacements = []  # list of (index, new_node)
                for i in range(1, num_bones + 1):
                    current_bone_name = rt.skinOps.GetBoneName(skin_mod, i, 0)
                    current_bone_node = rt.skinOps.GetBoneNode(skin_mod, i)
                    # Strip SRC_ prefix added during build phase before pattern matching
                    match_name = current_bone_name[4:] if current_bone_name.startswith("SRC_") else current_bone_name

                    for alias, props in sorted_mapping:
                        pattern = props.get("pattern", "")
                        target_name = props.get("target_bone", alias)
                        clean_pattern = pattern.replace("*", "")
                        if not clean_pattern: continue

                        if rt.matchPattern(match_name, pattern=f"*{clean_pattern}*"):
                            new_node = rt.getNodeByName(target_name)
                            if rt.isValidNode(new_node) and new_node != current_bone_node:
                                replacements.append((i, new_node))
                            break

                # Apply from highest index to lowest to keep indices valid.
                mesh_modified = False
                for i, new_node in sorted(replacements, key=lambda x: x[0], reverse=True):
                    try:
                        rt.skinOps.ReplaceBone(skin_mod, i, new_node)
                        count += 1
                        mesh_modified = True
                    except Exception as e:
                        print(f"Transfer Error idx={i}: {e}")

                if mesh_modified:
                    skin_mod.always_deform = False
                    skin_mod.always_deform = True

        except Exception as e:
            self.logger.error(f"Skin Error: {e}")
        finally:
            rt.resumeEditing()
            rt.redrawViews()

        self.logger.info(f"Skin Transfer Complete. Moved {count} bones.")


    # -----------------------------------------------------------------------
    # MAIN EXECUTION (FIXED HUB/LIMBS ATTRIBUTE ERROR)
    # -----------------------------------------------------------------------
    def run_process(self):
        self.log_text.clear()
        if not self.full_json_data:
            self.logger.warning("No JSON data loaded.")
            return

        RIG_NAME = self.full_json_data.get("rig_name", "MyCharacter")
        self.logger.info(f"--- Building Rig: {RIG_NAME} ---")

        with pymxs.undo(True), pymxs.animate(False):
            
            created_bones_map = {}
            build_queue = []
            temp_renamed_nodes = [] 

            # MASTER ROOT — use Dummy so it acts as a proper rig root (no mesh/render)
            master_root = rt.Dummy()
            master_root.name = RIG_NAME
            master_root.pos = rt.Point3(0, 0, 0)
            master_root.boxSize = rt.Point3(20, 20, 20)
            master_root.wirecolor = rt.color(255, 255, 0)
            
            
            self.logger.info("Phase 1: Pre-Renaming Sources...")
            
            for alias, props in self.current_mapping.items():
                src_node = self.resolve_fbx_node(props)
                if src_node:
                    depth = 0
                    temp = src_node
                    while temp.parent:
                        depth += 1
                        temp = temp.parent
                    
                    
                    build_queue.append((depth, alias, props, src_node))

            
            build_queue.sort(key=lambda x: x[0])

            # >>> (Anti-Conflict) <<<
            for item in build_queue:
                node = item[3] 
                
                if not node.name.startswith("SRC_"):
                    node.name = f"SRC_{node.name}"
                    temp_renamed_nodes.append(node)

            
            for depth, alias, props, src_node in build_queue:
                target_name = props.get("target_bone", alias)
                
                
                if "Toe" in props.get("pattern", "") and "Digit" in target_name:
                    if "L" in target_name: target_name = "LToe"
                    elif "R" in target_name: target_name = "RToe"
                
                final_name = target_name
                start_pos = src_node.transform.row4
                
                
                bone_end_pos = None
                
                
                is_pelvis = (alias == "Pelvis") or (target_name == "Pelvis")
                if is_pelvis:
                    best_child = None
                    max_dot = -1.0
                    for child in src_node.children:
                        
                        is_mapped = False
                        
                        
                        vec = rt.normalize(child.pos - src_node.pos)
                        if vec.z > max_dot: 
                            max_dot = vec.z
                            best_child = child
                    
                    if best_child and max_dot > 0.5:
                        bone_end_pos = best_child.pos
                    else:
                        bone_end_pos = start_pos + rt.point3(0,0,5)

                
                else:
                    
                    if src_node.children.count > 0:
                        bone_end_pos = src_node.children[0].pos
                    else:
                        # Scale default lengths by the rig's scale_factor from JSON
                        _sf = self.full_json_data.get("scale_factor", 1.0) or 1.0
                        default_len = 4.0 * _sf
                        if "Digit" in final_name or "Toe" in final_name: default_len = 1.5 * _sf
                        if "Head" in final_name: default_len = 8.0 * _sf
                        
                        
                        direction = rt.normalize(src_node.transform.row1)
                        if src_node.parent:
                             vec = src_node.pos - src_node.parent.pos
                             if rt.length(vec) > 0.001: direction = rt.normalize(vec)
                        
                        bone_end_pos = start_pos + (direction * default_len)

                
                z_axis_hint = rt.normalize(src_node.transform.row3)
                new_bone = rt.BoneSys.createBone(start_pos, bone_end_pos, z_axis_hint)
                
                
                new_bone.name = final_name 
                
                
                bone_len = rt.distance(start_pos, bone_end_pos)
                width_val = max(0.5, min(bone_len * 0.2, 6.0))
                if "Pelvis" in final_name: width_val = bone_len * 0.5
                
                new_bone.width = width_val
                new_bone.height = width_val
                new_bone.taper = 90
                new_bone.wirecolor = rt.color(40, 150, 255)
                
                created_bones_map[src_node] = new_bone
                self.logger.info(f"Created Clean: {final_name}")

            
            self.logger.info("--- Linking Hierarchy ---")
            for depth, alias, props, src_node in build_queue:
                if src_node in created_bones_map:
                    my_new_bone = created_bones_map[src_node]
                    parent_bone = self.find_nearest_mapped_ancestor(src_node, created_bones_map)
                    
                    if parent_bone:
                        my_new_bone.parent = parent_bone
                    elif my_new_bone.parent != master_root:
                        my_new_bone.parent = master_root

            
            self.transfer_skin_to_standard_rig()
            
            
            self.logger.info("Phase 4: Cleanup (Restore Source Names)...")
            for node in temp_renamed_nodes:
                if rt.isValidNode(node) and node.name.startswith("SRC_"):
                    node.name = node.name[4:]
            if temp_renamed_nodes:
                self.logger.info(f"Restored {len(temp_renamed_nodes)} source bone names.")

        self.logger.info(">>> RIG BUILT SUCCESSFULLY (Clean Names) <<<")
        self._capture_bind_pose_snapshot()
        rt.completeRedraw()

    #CAT RIG

    def find_default_rig_path(self):
        mxs_find = """
        (
            local paths = #(
                "C:\\\\Program Files\\\\Autodesk\\\\3ds Max 2025\\\\presets\\\\CAT\\\\CATRigs\\\\Base Human.rig",
                (GetDir #maxroot) + "presets\\\\CAT\\\\CATRigs\\\\Base Human.rig",
                (GetDir #maxroot) + "stdplugs\\\\CATRigs\\\\Base Human.rig",
                (GetDir #plugcfg) + "\\\\CAT\\\\CATRigs\\\\Base Human.rig",
                (GetDir #userScripts) + "\\\\CATRigs\\\\Base Human.rig"
            )
            local res = ""
            for p in paths do (if res == "" and doesFileExist p do res = p)
            res
        )
        """
        try:
            found_path = str(rt.execute(mxs_find))
            if found_path and os.path.exists(found_path):
                return found_path
        except:
            pass
        return ""

    def run_cat_process(self):
        from Cat_core import CATRigEngine

        preset_path, _ = QFileDialog.getOpenFileName(self, "Select Base Rig", self.find_default_rig_path(), "CAT Rig Files (*.rig)")
        if not preset_path:
            self.logger.error("Please select a .rig preset file first!")
            return

        engine = CATRigEngine(self.full_json_data, self.logger, preset_path)
        engine.build_from_mapping()

    

# ---------------------------------------------------------------------------
# 3. BATCH RETARGETING SYSTEM (CORE LOGIC)
# ---------------------------------------------------------------------------
class BatchRetargeter(QWidget):
    def __init__(self, main_ui):
        super().__init__()
        self.main_ui = main_ui
        self.setWindowTitle("Universal Retargeter (Source Mapper)")
        self.resize(550, 800)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint) 
        
        self.active_file_path = None
        self.source_bones = [] 
        self.mapping_ui_rows = {} 
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # ==========================================
        # 1. GROUP: INPUT & TOOLS
        # ==========================================
        grp_load = QGroupBox("1. Input Motion Source & Tools")
        
        
        l_load = QVBoxLayout() 
        
        
        h_imp = QHBoxLayout()
        btn_import = QPushButton("📂 Import Data (FBX/BVH)")
        btn_import.setFixedHeight(35)
        btn_import.setStyleSheet("font-weight: bold;")
        btn_import.clicked.connect(self.import_motion_data)
        h_imp.addWidget(btn_import)
        
        self.lbl_file = QLabel("No Data Loaded")
        h_imp.addWidget(self.lbl_file)
        
        l_load.addLayout(h_imp)
        l_load.addSpacing(10)   
        
        
        self.btn_ref = QPushButton("Insert Ref Frame")
        self.btn_ref.setToolTip("Shift keys +1 & Reset Frame 0")
        self.btn_ref.clicked.connect(self.insert_reference_frame)

        self.btn_visual = QPushButton("🦴 Visual Skeleton")
        self.btn_visual.setToolTip("Draw lines for manual adjustment")
        self.btn_visual.clicked.connect(self.create_visual_skeleton)

        self.btn_pose = QPushButton("🙆 Fix Arms")
        self.btn_pose.setToolTip("Rotate Arms Up manually")
        self.btn_pose.clicked.connect(self.fix_a_pose_arms)

        self.btn_scale = QPushButton("📏 Auto-Scale")
        self.btn_scale.setToolTip("Match Source Height to Target")
        self.btn_scale.clicked.connect(self.auto_match_scale)

        
        tools_list = [self.btn_ref, self.btn_visual, self.btn_pose, self.btn_scale]
        
        grid_tools = QGridLayout()
        grid_tools.setSpacing(5)
        
        
        columns = 4
        for i, btn in enumerate(tools_list):
            row = i // columns
            col = i % columns
            btn.setFixedHeight(30)
            btn.setEnabled(False) 
            grid_tools.addWidget(btn, row, col)

        l_load.addLayout(grid_tools) 
        
        grp_load.setLayout(l_load)
        main_layout.addWidget(grp_load)
        
        # ==========================================
        # 2. GROUP: MAPPING
        # ==========================================
        grp_map = QGroupBox("2. Bone Mapping Table")
        l_map = QVBoxLayout()
        
        # Toolbar Mapping
        h_map_tools = QHBoxLayout()
        btn_auto = QPushButton("✨ Auto-Guess")
        btn_auto.clicked.connect(self.run_auto_map)
        btn_save_map = QPushButton("💾 Save Map")
        btn_save_map.clicked.connect(self.save_mapping_file)
        btn_load_map = QPushButton("📂 Load Map")
        btn_load_map.clicked.connect(self.load_mapping_file)
        
        h_map_tools.addWidget(btn_auto)
        h_map_tools.addWidget(btn_save_map)
        h_map_tools.addWidget(btn_load_map)
        l_map.addLayout(h_map_tools)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Target Rig Bone", "Source Bone (Select)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        l_map.addWidget(self.table)
        
        grp_map.setLayout(l_map)
        main_layout.addWidget(grp_map)
        
        # ==========================================
        # 3. GROUP: EXECUTION
        # ==========================================
        grp_run = QGroupBox("3. Execution")
        l_run = QVBoxLayout()
        
        self.chk_pos = QCheckBox("Transfer Root Position (Hips)")
        self.chk_pos.setChecked(True)
        l_run.addWidget(self.chk_pos)
        
        btn_link = QPushButton("🔗 LINK RIG (Fixed Orient)")
        btn_link.setFixedHeight(45)
        btn_link.clicked.connect(self.perform_link)
        l_run.addWidget(btn_link)
        
        grp_run.setLayout(l_run)
        main_layout.addWidget(grp_run)
        
        self.setLayout(main_layout)

    # -----------------------------------------------------------------------
    # LOGIC: IMPORT DATA
    # -----------------------------------------------------------------------    
    def import_motion_data(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Motion", "", "Motion (*.fbx *.bvh)")
        if not f: return
        
        self.active_file_path = f
        self.lbl_file.setText(os.path.basename(f))
        
        
        self.cleanup_scene()
        
        self.main_ui.logger.info(f"Harvesting Data: {os.path.basename(f)}...")
        
        old_handles = set([o.inode.handle for o in rt.objects])
        created_bones = []

        try:
            is_bvh = f.lower().endswith(".bvh")
            
            if is_bvh:
                # >>> USE PYTHON IMPORTER <<<
                self.main_ui.logger.info("Using Python BVH Parser (No Hangs)...")
                importer = SimpleBVHImporter(f)
                importer.parse()
                
                
                # Measure target rig height from JSON-defined bone names.
                def _find_rig_node(keywords):
                    # First try JSON mapping target names, then fallback hardcoded names.
                    if self.main_ui.current_mapping:
                        for alias, props in self.main_ui.current_mapping.items():
                            if any(k in alias.lower() for k in keywords):
                                n = rt.getNodeByName(props.get("target_bone", alias))
                                if n: return n
                    for name in keywords:
                        n = rt.getNodeByName(name.capitalize())
                        if n: return n
                        n = rt.getNodeByName(name)
                        if n: return n
                    return None

                target_hips = _find_rig_node(["hips", "pelvis", "root"])
                target_head = _find_rig_node(["head", "skull"]) or _find_rig_node(["neck"])
                rig_height = 100.0
                if target_head and target_hips:
                    rig_height = rt.distance(target_head.pos, target_hips.pos)
                
                created_bones = importer.build_in_max(target_height=rig_height, logger=self.main_ui.logger)

                
                if not created_bones:
                    self.main_ui.logger.error("BVH Parse Failed or Empty.")
                    return
                
                
                self.source_bones = [b.name for b in created_bones]
                
            else:
                # >>> USE STANDARD MAX FBX IMPORT <<<
                f_max = f.replace("\\", "/")

                # "import" mode always creates new scene nodes (no merging into existing
                # character bones).  This ensures handle-comparison finds them even when
                # an identically-named skeleton is already in the scene.
                rt.execute('FBXImporterSetParam "Mode" "import"')
                rt.execute('FBXImporterSetParam "Animation" true')
                rt.execute('FBXImporterSetParam "Skins" false')
                rt.execute('FBXImporterSetParam "Cameras" false')
                rt.execute('FBXImporterSetParam "Lights" false')

                cmd = f'importFile @"{f_max}" #noPrompt using:FBXIMP'
                res = rt.execute(cmd)

                if not res:
                    self.main_ui.logger.error("FBX Import Failed! (Max returned FALSE — check file path or FBX plugin).")
                    return

                self.source_bones = []
                new_nodes = []
                rt.disableSceneRedraw()
                for o in rt.objects:
                    if o.inode.handle not in old_handles:
                        new_nodes.append(o)

                # Rename imported animation nodes with ANIM_ prefix so they don't
                # conflict with the character skeleton that uses the same bone names
                # (e.g. mixamorig:Hips exists twice after a Mixamo anim import).
                # rt.getNodeByName returns the first match — without the prefix it
                # would silently find the static character bone instead of the anim bone.
                for o in new_nodes:
                    if not o.name.startswith("ANIM_"):
                        o.name = f"ANIM_{o.name}"
                    self.source_bones.append(o.name)
                    try: o.wirecolor = rt.color(0, 255, 0)
                    except: pass
                    try: o.box = True
                    except: pass
                rt.enableSceneRedraw()

                if not self.source_bones:
                    self.main_ui.logger.warning(
                        "FBX imported but 0 new objects detected. "
                        "Check that the file contains skeleton/bone data."
                    )

            rt.redrawViews()
            self.source_bones.sort()
            
            if not self.source_bones:
                self.main_ui.logger.warning("Import ran, but 0 objects found.")
            else:
                self.main_ui.logger.info(f"Harvest Success: Found {len(self.source_bones)} bones.")
            
            
            self.populate_table()
            self.run_auto_map()
            
        except Exception as e:
            self.main_ui.logger.error(f"Import Error: {e}")
            import traceback
            traceback.print_exc() 
            rt.enableSceneRedraw()

        
        
        
        self.btn_ref.setEnabled(True)
        self.btn_scale.setEnabled(True)
        self.btn_pose.setEnabled(True)
        self.btn_visual.setEnabled(True)
        
        self.main_ui.logger.info("Import Done. Tools Enabled.")


    def cleanup_scene(self):
        to_delete = []
        PREFIXES = ("BVH_", "ANIM_", "GHOST_", "DEBUG_RED_", "VECTOR_BLUE_", "LINE_")
        for o in rt.objects:
            if o.name.startswith(PREFIXES):
                to_delete.append(o)
        if to_delete: rt.delete(to_delete)

    # -----------------------------------------------------------------------
    # LOGIC: TABLE & MAPPING
    # -----------------------------------------------------------------------
    def populate_table(self):
        if not self.main_ui.current_mapping:
            QMessageBox.warning(self, "Error", "Please Load 'Profile_Mixamo.json' first in the main window.")
            return

        self.table.setRowCount(0)
        self.mapping_ui_rows = {}
        
        
        ordered_keys = list(self.main_ui.current_mapping.keys())
        
        for alias in ordered_keys:
            props = self.main_ui.current_mapping[alias]
            target_name = props.get("target_bone", alias)
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            
            item_lbl = QTableWidgetItem(f"{target_name} ({alias})")
            item_lbl.setToolTip(f"Pattern in JSON: {props.get('pattern','')}")
            
            
            if "Hips" in alias or "Root" in alias:
                item_lbl.setBackground(QColor("#333344"))
                item_lbl.setForeground(QColor("#FFDD55"))
            
            self.table.setItem(row, 0, item_lbl)
            
            # Col 1: Combo Box
            combo = self.create_bone_combo()
            self.table.setCellWidget(row, 1, combo)
            
            self.mapping_ui_rows[alias] = combo

    def create_bone_combo(self):
        from PySide6.QtWidgets import QComboBox
        combo = QComboBox()
        combo.addItem("--- None ---", "")
        # Add source bones
        for b in self.source_bones:
            combo.addItem(b, b)
        return combo

    # -----------------------------------------------------------------------
    # FUNCTION: INSERT T-POSE FRAME (SMART: DETECT BVH vs FBX)
    # -----------------------------------------------------------------------
    def insert_reference_frame(self):
        self.main_ui.logger.info("Inserting Reference Frame at 0...")

        if not self.source_bones:
            QMessageBox.warning(self, "Error", "No source bones found.")
            return

        nodes_to_process = []
        for name in self.source_bones:
            n = rt.getNodeByName(name)
            if n: nodes_to_process.append(n)

        if not nodes_to_process: return

        rt.suspendEditing()
        try:
            # Capture root positions at frame 0 BEFORE shifting keys.
            # BUG 6 FIX: A "root" is any node whose parent is NOT in the source set
            # (handles BVH roots that may have a wrapper Dummy as parent).
            rt.sliderTime = 0
            source_set = set(self.source_bones)
            root_positions = {}
            for node in nodes_to_process:
                if not node.parent or node.parent.name not in source_set:
                    root_positions[node.inode.handle] = (node.pos.x, node.pos.y, node.pos.z)

            # Shift all keys by exactly 1 frame ("1f" = 1 frame, "1" would be 1 tick).
            rt.select(nodes_to_process)
            rt.execute("moveKeys selection 1f")

            rt.sliderTime = 0
            with pymxs.animate(True):
                for node in nodes_to_process:
                    h = node.inode.handle
                    is_root = h in root_positions
                    if not is_root:
                        cmd = f"""
                        t = maxOps.getNodeByHandle {h}
                        in coordsys parent t.rotation = (quat 0 0 0 1)
                        """
                        rt.execute(cmd)
                    else:
                        px, py, pz = root_positions[h]
                        cmd = f"""
                        t = maxOps.getNodeByHandle {h}
                        t.rotation = (quat 0 0 0 1)
                        t.pos = [{px}, {py}, {pz}]
                        """
                        rt.execute(cmd)

            self.main_ui.logger.info("✅ Frame 0 Generated. (Structure Preserved).")
            rt.redrawViews()
            self.main_ui.logger.info("TIP: If not in T-Pose, use 'Fix Arms' button now.")

        except Exception as e:
            self.main_ui.logger.error(f"Ref Frame Error: {e}")
            import traceback; traceback.print_exc()
        finally:
            rt.resumeEditing()

    # -----------------------------------------------------------------------
    # LOGIC: AUTO-GUESS & SAVE/LOAD
    # -----------------------------------------------------------------------
    def run_auto_map(self):
        
        self.main_ui.logger.info("Auto-guessing bones...")
        
        # 1.
        synonyms = {
            "hips": ["root", "pelvis", "hip", "bip001_pelvis"],
            "spine": ["spine1", "lowertorso", "bip001_spine"],
            "chest": ["spine2", "ribcage", "uppertorso", "spine3", "bip001_spine1"],
            "neck": ["neck1", "head_neck", "bip001_neck"],
            "head": ["head1", "bip001_head"],
            
            # Left
            "leftshoulder": ["l_clavicle", "clavicle_l", "collar_l", "l_collar", "shoulder_l"],
            "leftarm": ["l_upperarm", "upperarm_l", "l_arm", "arm_l", "l_shldr", "bip001_l_upperarm"],
            "leftforearm": ["l_forearm", "forearm_l", "elbow_l", "l_elbow", "bip001_l_forearm"],
            "lefthand": ["l_hand", "hand_l", "wrist_l", "l_wrist", "bip001_l_hand"],
            
            "leftupleg": ["l_thigh", "thigh_l", "upperleg_l", "l_up_leg", "hip_l", "bip001_l_thigh"],
            "leftleg": ["l_calf", "calf_l", "lowerleg_l", "l_leg", "shin_l", "knee_l", "bip001_l_calf"],
            "leftfoot": ["l_foot", "foot_l", "ankle_l", "l_ankle", "bip001_l_foot"],
            
            # Right (Mirror of Left)
            "rightshoulder": ["r_clavicle", "clavicle_r", "collar_r", "r_collar", "shoulder_r"],
            "rightarm": ["r_upperarm", "upperarm_r", "r_arm", "arm_r", "r_shldr", "bip001_r_upperarm"],
            "rightforearm": ["r_forearm", "forearm_r", "elbow_r", "r_elbow", "bip001_r_forearm"],
            "righthand": ["r_hand", "hand_r", "wrist_r", "r_wrist", "bip001_r_hand"],
            
            "rightupleg": ["r_thigh", "thigh_r", "upperleg_r", "r_up_leg", "hip_r", "bip001_r_thigh"],
            "rightleg": ["r_calf", "calf_r", "lowerleg_r", "r_leg", "shin_r", "knee_r", "bip001_r_calf"],
            "rightfoot": ["r_foot", "foot_r", "ankle_r", "r_ankle", "bip001_r_foot"],
        }
        
        # 2.
        # { "hips": "BVH_Hips", "leftarm": "BVH_LeftArm" }
        source_clean_map = {}
        for real_name in self.source_bones:
            clean = (real_name.lower()
                     .split(":")[-1]
                     .replace("anim_", "")
                     .replace("bvh_", "")
                     .replace("mixamorig", "")
                     .replace(" ", "")
                     .replace("_", ""))
            source_clean_map[clean] = real_name
            source_clean_map[real_name.lower()] = real_name

        
        match_count = 0
        for alias, combo in self.mapping_ui_rows.items():
            
            props = self.main_ui.current_mapping[alias]
            pattern = props.get("pattern", "").lower() # mixamorig:RightUpLeg
            core_keyword = pattern.split(":")[-1] # RightUpLeg
            
            
            found_real_name = None
            
            
            clean_core = core_keyword.replace("_", "").lower()
            if clean_core in source_clean_map:
                found_real_name = source_clean_map[clean_core]
                
            
            if not found_real_name and clean_core in synonyms:
                possible_names = synonyms[clean_core]
                for p in possible_names:
                    p_clean = p.replace("_", "")
                    if p_clean in source_clean_map:
                        found_real_name = source_clean_map[p_clean]
                        break
            
            
            if not found_real_name:
                alias_clean = alias.lower().replace("_", "")
                if alias_clean in source_clean_map:
                     found_real_name = source_clean_map[alias_clean]

            
            if found_real_name:
                idx = combo.findData(found_real_name)
                if idx >= 0: 
                    combo.setCurrentIndex(idx)
                    match_count += 1
        
        self.main_ui.logger.info(f"Auto-guessed {match_count} bones.")

    def save_mapping_file(self):
        
        f, _ = QFileDialog.getSaveFileName(self, "Save Mapping", "", "JSON (*.json)")
        if not f: return
        
        save_data = {}
        for alias, combo in self.mapping_ui_rows.items():
            selected_bone = combo.currentData()
            if selected_bone:
                save_data[alias] = selected_bone
        
        with open(f, 'w') as outfile:
            json.dump(save_data, outfile, indent=4)
        
        self.main_ui.logger.info(f"Mapping saved to: {os.path.basename(f)}")
        QMessageBox.information(self, "Saved", "Mapping saved successfully!\nNext time, just load this file.")

    def load_mapping_file(self):
       
        f, _ = QFileDialog.getOpenFileName(self, "Load Mapping", "", "JSON (*.json)")
        if not f: return
        
        try:
            with open(f, 'r') as infile:
                loaded_data = json.load(infile)
            
            match_count = 0
            for alias, target_bone_name in loaded_data.items():
                if alias in self.mapping_ui_rows:
                    combo = self.mapping_ui_rows[alias]
                    
                    idx = combo.findData(target_bone_name)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                        match_count += 1
                    else:
                        
                        pass
            
            self.main_ui.logger.info(f"Loaded mapping: Applied {match_count} bones.")
            
        except Exception as e:
             self.main_ui.logger.error(f"Load Map Error: {e}")

    def auto_match_scale(self):
        self.main_ui.logger.info("Auto-Scaling Source...")

        def get_node_fuzzy(names_list):
            for n in names_list:
                node = rt.getNodeByName(n)
                if node: return node
            return None

        # Build target-bone name candidates from JSON mapping (prefer JSON names over hard-coded).
        root_candidates = ["Hips", "Pelvis", "Root", "Bip001 Pelvis", "Hip", "Master"]
        head_candidates = ["Head", "Bip001 Head", "Head1", "Skull"]
        neck_candidates = ["Neck", "Neck1", "Bip001 Neck"]

        if self.main_ui.current_mapping:
            for alias, props in self.main_ui.current_mapping.items():
                tgt = props.get("target_bone", alias)
                al  = alias.lower()
                if any(k in al for k in ["hips", "pelvis", "root"]):
                    if tgt not in root_candidates: root_candidates.insert(0, tgt)
                elif any(k in al for k in ["head", "skull"]):
                    if tgt not in head_candidates: head_candidates.insert(0, tgt)
                elif any(k in al for k in ["neck"]):
                    if tgt not in neck_candidates: neck_candidates.insert(0, tgt)

        t_root = get_node_fuzzy(root_candidates)
        t_head = get_node_fuzzy(head_candidates)

        if not t_head:
            self.main_ui.logger.warning("Target 'Head' not found, trying 'Neck' for height reference...")
            t_head = get_node_fuzzy(neck_candidates)

        
        s_root_name = self.find_best_source_bone(["hips", "root", "pelvis", "master"])
        s_head_name = self.find_best_source_bone(["head", "skull", "neck"])
        
        
        if not t_root or not t_head:
            QMessageBox.warning(self, "Scale Error",
                "Could not find Target Rig bones in the scene.\n\n"
                "Auto-Scale needs the built rig to measure against.\n\n"
                "Correct order:\n"
                "  1. Load FBX character + JSON\n"
                "  2. Click BUILD STANDARD RIG (main window)\n"
                "  3. Import BVH / FBX animation\n"
                "  4. Then press Auto-Scale")
            return

        if not s_root_name or not s_head_name:
            QMessageBox.warning(self, "Scale Error", "Could not identify Source Root or Head from the mapping table.")
            return

        s_root = rt.getNodeByName(s_root_name)
        s_head = rt.getNodeByName(s_head_name)
        
        
        h_target = rt.distance(t_root.pos, t_head.pos)
        h_source = rt.distance(s_root.pos, s_head.pos)
        
        
        if h_source < 0.1:
            self.main_ui.logger.error("Source height is too small (Zero distance). Cannot scale.")
            return

        scale_factor = h_target / h_source
        
        self.main_ui.logger.info(f"Height Target: {round(h_target,2)} | Height Source: {round(h_source,2)}")
        
        
        top_node = s_root
        while top_node.parent and (top_node.parent.name in self.source_bones):
            top_node = top_node.parent

        # BUG 5 FIX: reset scale to 1 first, re-measure, then apply once.
        with pymxs.animate(False):
            top_node.scale = rt.point3(1, 1, 1)

        # Re-measure after reset so factor is always relative to unscaled skeleton.
        h_source = rt.distance(s_root.pos, s_head.pos)
        if h_source < 0.1:
            self.main_ui.logger.error("Source height is too small after reset. Cannot scale.")
            return
        scale_factor = h_target / h_source

        with pymxs.animate(False):
            top_node.scale = rt.point3(scale_factor, scale_factor, scale_factor)

        self.main_ui.logger.info(f"✅ Scaled Source by factor: {round(scale_factor, 4)}")
        rt.redrawViews()


    def find_best_source_bone(self, keywords):
        
        if isinstance(keywords, str): keywords = [keywords]
        
        
        clean_keys = [k.lower().replace(" ", "").replace("_", "") for k in keywords]
        
        for alias, combo in self.mapping_ui_rows.items():
            
            props = self.main_ui.current_mapping.get(alias)
            target_name = props.get("target_bone", alias)
            
            
            clean_alias = alias.lower().replace(" ", "").replace("_", "")
            clean_target = target_name.lower().replace(" ", "").replace("_", "")
            
            
            for key in clean_keys:
                
                if (key in clean_alias) or (key in clean_target):
                   
                    selected_source = combo.currentData()
                    if selected_source:
                        return selected_source
        
        return None
    
    def fix_a_pose_arms(self):
        self.main_ui.logger.info("Fixing A-Pose (Arms +85 deg)...")
        rt.sliderTime = 0
        
        
        l_name = self.find_best_source_bone(["leftarm", "l_upperarm", "l_arm", "arm_l"])
        r_name = self.find_best_source_bone(["rightarm", "r_upperarm", "r_arm", "arm_r"])
        
        if not l_name and not r_name:
            QMessageBox.warning(self, "Error", "Could not identify Arm bones in the mapping table.\nCheck if rows exist for 'LeftArm' or 'L_UpperArm'.")
            return

        with pymxs.animate(False):
            # BUG 7 FIX: use the bone's own forward axis (row1) for roll.
            # For most rigs row1 points along the bone; rotating around it
            # lifts arms from A-pose to T-pose. row3 (Z) is wrong for many rigs.
            if l_name:
                l_node = rt.getNodeByName(l_name)
                if l_node:
                    axis = rt.normalize(l_node.transform.row1)
                    rt.rotate(l_node, rt.angleaxis(85, axis))
                    self.main_ui.logger.info(f"Rotated Left: {l_name}")
                else:
                    self.main_ui.logger.warning(f"Node '{l_name}' not found in scene.")

            if r_name:
                r_node = rt.getNodeByName(r_name)
                if r_node:
                    axis = rt.normalize(r_node.transform.row1)
                    rt.rotate(r_node, rt.angleaxis(-85, axis))
                    self.main_ui.logger.info(f"Rotated Right: {r_name}")
                else:
                    self.main_ui.logger.warning(f"Node '{r_name}' not found in scene.")
        
        rt.redrawViews()

    # -----------------------------------------------------------------------
    # FUNCTION: VISUALIZE SKELETON (DRAW LINES)
    # -----------------------------------------------------------------------
    def create_visual_skeleton(self):
        self.main_ui.logger.info("Creating Visual Skeleton Lines...")
        
        if not self.source_bones:
            QMessageBox.warning(self, "Error", "No source bones found.")
            return

        rt.suspendEditing()
        count = 0
        try:
            lyr_name = "VISUAL_LINES"
            if not rt.LayerManager.getLayerFromName(lyr_name): 
                rt.LayerManager.newLayerFromName(lyr_name)
            layer = rt.LayerManager.getLayerFromName(lyr_name)
            
            for name in self.source_bones:
                node = rt.getNodeByName(name)
                if not node: continue
                
                
                try:
                    
                    node.boneEnable = True
                    node.showLinks = True
                    node.pos.controller.isShown = False
                    count += 1
                except:
                    
                    if node.children.count > 0:
                        child = node.children[0]
                        
                        s = rt.SplineShape(pos=node.pos)
                        s.name = f"LINE_{node.name}"
                        s.wirecolor = rt.color(255, 255, 0)
                        
                        rt.addNewSpline(s)
                        
                        
                        rt.addKnot(s, 1, rt.name("corner"), rt.name("line"), node.pos)
                        rt.addKnot(s, 1, rt.name("corner"), rt.name("line"), child.pos)
                        
                        rt.updateShape(s)
                        
                        s.parent = node
                        layer.addNode(s)
                        s.isFrozen = True 

            self.main_ui.logger.info(f"✅ Skeleton Visualized on {count} bones.")
            rt.redrawViews()
            
        except Exception as e:
            self.main_ui.logger.error(f"Visualizer Error: {e}")
            import traceback; traceback.print_exc()
        finally:
            rt.resumeEditing()

    # -----------------------------------------------------------------------
    # LOGIC: EXECUTE LINK
    # -----------------------------------------------------------------------
    def perform_link(self):
        lyr_name = "RETARGET_HELPERS"
        if not rt.LayerManager.getLayerFromName(lyr_name):
            rt.LayerManager.newLayerFromName(lyr_name)
        layer = rt.LayerManager.getLayerFromName(lyr_name)
        layer.current = True

        # BUG 1 FIX: cleanup stale ghosts from previous run
        stale = [o for o in rt.objects if o.name.startswith("GHOST_ROT_") or o.name.startswith("GHOST_POS_")]
        if stale:
            rt.delete(stale)

        count = 0
        rt.suspendEditing()

        try:
            rt.sliderTime = 0

            with pymxs.animate(False):
                for alias, combo in self.mapping_ui_rows.items():
                    src_name = combo.currentData()
                    if not src_name: continue

                    src_node = rt.getNodeByName(src_name)
                    props = self.main_ui.current_mapping.get(alias)
                    if not props: continue
                    target_name = props.get("target_bone", alias)
                    tgt_node = rt.getNodeByName(target_name)

                    if not src_node:
                        self.main_ui.logger.warning(f"Link: source '{src_name}' not in scene (alias={alias})")
                        continue
                    if not tgt_node:
                        self.main_ui.logger.warning(f"Link: target bone '{target_name}' not in scene — build the rig first (alias={alias})")
                        continue

                    rt.setTransformLockFlags(tgt_node, rt.name("none"))

                    # ── Bind-pose reference ──────────────────────────────────────
                    # BVH: frame 0 = T-pose (after insert_reference_frame).
                    # ANIM_ FBX: use the original character bone's bind pose,
                    # but strip scale so it matches the unscaled ANIM_ node (BUG 3 FIX).
                    src_bind_tm = src_node.transform
                    if src_name.startswith("ANIM_"):
                        cb = rt.getNodeByName(src_name[5:])
                        if cb and rt.isValidNode(cb):
                            src_bind_tm = cb.transform

                    tgt_bind_tm = tgt_node.transform

                    # BUG 2 FIX: normalize rows to strip scale before computing correction.
                    def rot_only_normalized(tm):
                        r1 = rt.normalize(tm.row1)
                        r2 = rt.normalize(tm.row2)
                        r3 = rt.normalize(tm.row3)
                        return rt.matrix3(r1, r2, r3, rt.point3(0, 0, 0))

                    correction = rot_only_normalized(tgt_bind_tm) * rt.inverse(rot_only_normalized(src_bind_tm))

                    # --- ROTATION GHOST ---
                    rot_ghost = rt.Point(size=2, box=False, cross=True, wirecolor=rt.color(255, 0, 255))
                    rot_ghost.name = f"GHOST_ROT_{alias}"
                    rot_ghost.parent = src_node
                    ghost_rot_now = correction * rot_only_normalized(src_node.transform)
                    rot_ghost.transform = rt.matrix3(
                        ghost_rot_now.row1, ghost_rot_now.row2, ghost_rot_now.row3,
                        src_node.pos
                    )

                    t_h = tgt_node.inode.handle
                    g_h = rot_ghost.inode.handle

                    cmd = f"""
                    t = maxOps.getNodeByHandle {t_h}
                    g = maxOps.getNodeByHandle {g_h}
                    if (isValidNode t and isValidNode g) do (
                        t.rotation.controller = Orientation_Constraint()
                        t.rotation.controller.appendTarget g 100.0
                        t.rotation.controller.relative = false
                    )
                    """
                    rt.execute(cmd)

                    # --- POSITION (root bone only) ---
                    a_lower = alias.lower()
                    is_root = any(x in a_lower for x in ["hips", "root", "pelvis", "bip01"])

                    if is_root and self.chk_pos.isChecked():
                        # BUG 4 FIX: compute offset and place ghost using world-space
                        # transMatrix directly (not relative to parent).
                        # Since root src_node typically has no parent, this is safe.
                        # After parenting, Max stores the local offset correctly.
                        tgt_pos = rt.point3(tgt_bind_tm.row4.x, tgt_bind_tm.row4.y, tgt_bind_tm.row4.z)
                        src_pos = rt.point3(src_bind_tm.row4.x, src_bind_tm.row4.y, src_bind_tm.row4.z)
                        pos_offset = tgt_pos - src_pos

                        pos_ghost = rt.Point(size=3, box=True, cross=False, wirecolor=rt.color(0, 255, 0))
                        pos_ghost.name = f"GHOST_POS_{alias}"
                        pos_ghost.parent = src_node
                        pos_ghost.transform = rt.transMatrix(src_node.pos + pos_offset)

                        gp_h = pos_ghost.inode.handle
                        cmd_pos = f"""
                        t = maxOps.getNodeByHandle {t_h}
                        gp = maxOps.getNodeByHandle {gp_h}
                        if (isValidNode t and isValidNode gp) do (
                            t.pos.controller = Position_Constraint()
                            t.pos.controller.appendTarget gp 100.0
                            t.pos.controller.relative = false
                        )
                        """
                        rt.execute(cmd_pos)

                    count += 1

            if count > 0:
                self.main_ui.logger.info(f"Link Success: {count} bones linked.")
                QMessageBox.information(self, "Success", "Retargeting Complete!")
            else:
                self.main_ui.logger.warning("No bones linked.")

        except Exception as e:
            self.main_ui.logger.error(f"Link Error: {e}")
        finally:
            rt.resumeEditing()
            rt.redrawViews()
 