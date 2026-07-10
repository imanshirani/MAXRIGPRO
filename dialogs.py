import json
import re
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QLineEdit, QLabel, QApplication, 
                               QPushButton, QGroupBox, QTextEdit, QMessageBox, QFileDialog, QAbstractItemView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import pymxs
rt = pymxs.runtime


from widgets import MatrixCellWidget

# ---------------------------------------------------------------------------
# LIVE CALIBRATION TOOL (THE FINAL SOLUTION)
# ---------------------------------------------------------------------------
class LiveCalibrator(QDialog):
    def __init__(self, main_ui, parent=None):
        super(LiveCalibrator, self).__init__(parent)
        self.setWindowTitle("🛠️ Calibrator: Pink Ghost && Blue Reference")
        self.resize(600, 650)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint) 
        
        self.main_ui = main_ui
        self.current_alias = None
        
        layout = QVBoxLayout()
        
        
        lbl = QLabel("1. Select Bone -> Pink Ghost && Blue Box appear.\n2. Align Pink Ghost's RED Arrow to Blue Box's RED Arrow.\n   (Blue Box = True Bone Direction)\n3. Click 'Get Matrix'.")
        lbl.setStyleSheet("color: #AAA; margin-bottom: 8px; font-style: italic;")
        layout.addWidget(lbl)
        
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Filter:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search...")
        self.txt_search.textChanged.connect(self.filter_list) 
        search_layout.addWidget(self.txt_search)
        layout.addLayout(search_layout)
        
        
        self.list_widget = QTableWidget()
        self.list_widget.setColumnCount(3)
        self.list_widget.setHorizontalHeaderLabels(["Alias", "Target Bone", "FBX Source"]) 
        header = self.list_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.list_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.list_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list_widget.clicked.connect(self.create_or_select_ghost)
        layout.addWidget(self.list_widget)
        
        
        btn_inspect = QPushButton("🔍 Show Actual FBX Matrix (Debug)")
        btn_inspect.setStyleSheet("background-color: #444; color: #BBB; border: 1px solid #555;")
        btn_inspect.clicked.connect(self.inspect_source_bone)
        layout.addWidget(btn_inspect)

        
        grp_data = QGroupBox("Generated Matrix (Difference)")
        l_data = QVBoxLayout()
        
        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setMaximumHeight(80)
        self.txt_output.setStyleSheet("font-family: Consolas; color: #00FF00; background: #222;")
        l_data.addWidget(self.txt_output)
        
        self.btn_get = QPushButton("📋 GET MATRIX (Copy to Clipboard)")
        self.btn_get.setFixedHeight(50)
        self.btn_get.clicked.connect(self.calculate_and_copy)
        l_data.addWidget(self.btn_get)
        
        grp_data.setLayout(l_data)
        layout.addWidget(grp_data)

        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_status)
        
        self.setLayout(layout)
        self.populate_list()

    def populate_list(self):
        self.list_widget.setRowCount(0)
        row = 0
        for alias in sorted(self.main_ui.current_mapping.keys()):
            self.list_widget.insertRow(row)
            props = self.main_ui.current_mapping.get(alias, {})
            self.list_widget.setItem(row, 0, QTableWidgetItem(alias))
            
            Rigg_item = QTableWidgetItem(props.get("target_bone", ""))
            Rigg_item.setForeground(QColor("#AAAAAA"))
            self.list_widget.setItem(row, 1, Rigg_item)
            
            fbx_item = QTableWidgetItem(props.get("pattern", ""))
            fbx_item.setForeground(QColor("#00AAAA"))
            self.list_widget.setItem(row, 2, fbx_item)
            row += 1

    def filter_list(self, text):
        search_text = text.lower()
        for r in range(self.list_widget.rowCount()):
            match = False
            for c in range(3):
                item = self.list_widget.item(r, c)
                if item and search_text in item.text().lower(): match = True
            self.list_widget.setRowHidden(r, not match)

    def create_or_select_ghost(self):
        row = self.list_widget.currentRow()
        if row < 0: return
        alias = self.list_widget.item(row, 0).text()
        self.current_alias = alias
        
        props = self.main_ui.current_mapping.get(alias)
        src_node = self.main_ui.resolve_fbx_node(props)
        
        if not src_node:
            self.lbl_status.setText("Source FBX bone not found!")
            return

        
        ghost_name = f"GHOST_{alias}"
        ghost = rt.getNodeByName(ghost_name)
        if not ghost:
            ghost = rt.Point(pos=src_node.pos, size=2, axis=True, box=False, cross=True, wirecolor=rt.color(255, 0, 255))
            ghost.name = ghost_name
        # Always refresh transform — ghost may have been created stale by create_ghost_helpers()
        correction_tm = self.main_ui.get_correction_matrix(props)
        ghost.transform = src_node.transform * correction_tm
        
        
        blue_name = f"VECTOR_BLUE_{alias}"
        old_blue = rt.getNodeByName(blue_name)
        if old_blue: rt.delete(old_blue)

        target_child = None
        try: target_child = self.main_ui.get_mapped_child(src_node)
        except: pass
        
        
        if not target_child and src_node.children.count > 0:
            target_child = src_node.children[0]
            
        blue_tm = None
        
        
        if target_child:
            vec = target_child.pos - src_node.pos
            length = rt.length(vec)
            if length > 0.001:
                x_axis = rt.normalize(vec)
                up_hint = rt.normalize(src_node.transform.row3)
                if abs(rt.dot(x_axis, up_hint)) > 0.95: up_hint = rt.point3(0,0,1)
                z_axis = rt.normalize(rt.cross(x_axis, up_hint))
                y_axis = rt.normalize(rt.cross(z_axis, x_axis))
                blue_tm = rt.matrix3(x_axis, y_axis, z_axis, src_node.pos)
        
        
        else:
            x_axis = rt.normalize(src_node.transform.row1) 
            y_axis = rt.normalize(src_node.transform.row2)
            z_axis = rt.normalize(src_node.transform.row3)
            blue_tm = rt.matrix3(x_axis, y_axis, z_axis, src_node.pos)

        if blue_tm:
            blue = rt.Point(pos=src_node.pos, size=1.0, wirecolor=rt.color(0, 180, 255), box=True, axis=True, cross=False)
            blue.name = blue_name
            blue.transform = blue_tm
            blue.showFrozenInGray = False 
            
            self.lbl_status.setText(f"Target: {alias}\n1. See BLUE BOX (Target Direction)\n2. Align PINK CROSS to match Blue.")
            self.lbl_status.setStyleSheet("color: #00FF00;")
        else:
            self.lbl_status.setText(f"Target: {alias}\n⚠️ No Child found (Align manually without guide)")
            self.lbl_status.setStyleSheet("color: orange;")
        
        

    def inspect_source_bone(self):
        if not self.current_alias: return
        props = self.main_ui.current_mapping.get(self.current_alias)
        src_node = self.main_ui.resolve_fbx_node(props)
        if src_node:
            tm = src_node.transform
            QMessageBox.information(self, "Bone Inspector", f"Bone: {src_node.name}\n\n{tm}")

    def calculate_and_copy(self):
        if not self.current_alias: return
        
        props = self.main_ui.current_mapping.get(self.current_alias)
        src_node = self.main_ui.resolve_fbx_node(props)
        ghost_name = f"GHOST_{self.current_alias}"
        ghost = rt.getNodeByName(ghost_name)
        
        if not src_node or not ghost:
            QMessageBox.warning(self, "Error", "Ghost or Source missing.")
            return
            
        try:
            correction_tm = rt.inverse(src_node.transform) * ghost.transform
            
            vx = rt.normalize(correction_tm.row1)
            vy_temp = rt.normalize(correction_tm.row2)
            vz = rt.normalize(rt.cross(vx, vy_temp))
            vy = rt.normalize(rt.cross(vz, vx))
            
            def clean(val): 
                if abs(val - round(val)) < 0.001: return int(round(val))
                return float(round(val, 4))

            r1 = [clean(vx.x), clean(vx.y), clean(vx.z)]
            r2 = [clean(vy.x), clean(vy.y), clean(vy.z)]
            r3 = [clean(vz.x), clean(vz.y), clean(vz.z)]
            
            pos = correction_tm.row4
            r4 = [clean(pos.x), clean(pos.y), clean(pos.z)]
            
            final_data = [r1, r2, r3, r4]
            data_str = json.dumps(final_data).replace(" ", "")
            
            self.txt_output.setText(data_str)
            QApplication.clipboard().setText(data_str)
            
            self.lbl_status.setText(f"✅ Copied! Ready to Paste.")
            self.lbl_status.setStyleSheet("color: #00FF00; font-weight: bold;")

        except Exception as e:
            QMessageBox.critical(self, "Math Error", str(e))


# ---------------------------------------------------------------------------
# 1. MAPPING EDITOR (COMMAND CENTER)
# ---------------------------------------------------------------------------
class MappingEditor(QDialog):
    def __init__(self, full_json_data, parent=None):
        super(MappingEditor, self).__init__(parent)
        self.setWindowTitle("Rig Configuration Editor (Full Mode)")
        self.resize(900, 600) 
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)

        self.main_ui = parent 
        self.full_data = full_json_data if full_json_data else {}
        self.mapping_data = self.full_data.get("mapping", {})
        self.active_vector_widget = None 
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # --- Header ---
        rig_n = self.full_data.get("rig_name", "MyCharacter")
        layout.addWidget(QLabel(f"Target Rig Name: {rig_n}"))

        # --- Search Filter ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Filter:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search Bone Name...")
        self.txt_search.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.txt_search)
        layout.addLayout(search_layout)

        # --- Table (8 Columns) ---
        self.table = QTableWidget()
        self.table.setColumnCount(8) 
        self.table.setHorizontalHeaderLabels([
            "Alias", "Bone Suffix", "Param Name", "FBX Pattern", 
            "Mode", "Method", "Transform Matrix", "Status"
        ])

        
        self.table.setDragEnabled(False) 
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        # Hide "Method" column — it's auto-filled as DEFAULT and not user-facing.
        self.table.setColumnHidden(5, True)

        self.load_table_data()
        layout.addWidget(self.table)
        
        # --- Matrix Controls ---
        ctrl_group = QGroupBox("Matrix Controls (Manual Adjustments)")        
        ctrl_group.setMinimumHeight(60)
        ctrl_layout = QHBoxLayout()
        self.lbl_status = QLabel("Select a matrix cell...")
        self.lbl_status.setStyleSheet("color: gray;")
        ctrl_layout.addWidget(self.lbl_status)
        
        btn_reset = QPushButton("♻️ Reset"); btn_reset.clicked.connect(self.reset_active_vector)
        btn_rot_x = QPushButton("Rot X +90"); btn_rot_x.clicked.connect(lambda: self.rotate_active_vector("x"))
        btn_rot_y = QPushButton("Rot Y +90"); btn_rot_y.clicked.connect(lambda: self.rotate_active_vector("y"))
        btn_rot_z = QPushButton("Rot Z +90"); btn_rot_z.clicked.connect(lambda: self.rotate_active_vector("z"))

        ctrl_layout.addStretch()
        ctrl_layout.addWidget(btn_reset); ctrl_layout.addWidget(btn_rot_x)
        ctrl_layout.addWidget(btn_rot_y); ctrl_layout.addWidget(btn_rot_z)
        ctrl_group.setLayout(ctrl_layout)
        layout.addWidget(ctrl_group)

        # ==========================================================
        # >>> NEW GROUP: TOOLS & SAVING (No Build Here) <<<
        # ==========================================================
        tools_group = QGroupBox("Tools && Saving")
        tools_layout = QHBoxLayout()
        
        # 1. Visual Calibrator
        btn_calib = QPushButton("🛠️ Visual Calibrator")        
        btn_calib.setToolTip("Open Visual Helper Tool")
        btn_calib.setFixedHeight(40)
        btn_calib.clicked.connect(self.launch_calibrator)
        
        
        btn_save = QPushButton("💾 Save JSON File")
        btn_save.setToolTip("Save current mapping to a .json file")
        btn_save.setFixedHeight(40)
        btn_save.clicked.connect(self.save_to_json) 
        
        tools_layout.addWidget(btn_calib)
        tools_layout.addWidget(btn_save)
        
        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

        # ==========================================================
        # >>> FOOTER LAYOUT (Add/Remove Left | Apply Right) <<<
        # ==========================================================
        
        footer_group = QGroupBox("Row Actions")
        footer_group.setMinimumHeight(60)       
        footer_layout = QHBoxLayout(footer_group)
        footer_layout.setContentsMargins(10, 15, 10, 10)

        # Left: Row Operations
        btn_up = QPushButton("⬆️ Move Up")
        btn_up.setFixedWidth(90)
        btn_up.clicked.connect(self.move_row_up)

        btn_down = QPushButton("⬇️ Move Down")
        btn_down.setFixedWidth(90)
        btn_down.clicked.connect(self.move_row_down)

        btn_add = QPushButton("➕ Add Row")
        btn_add.setFixedWidth(80)
        btn_add.clicked.connect(self.add_row)
        
        btn_rem = QPushButton("❌ Remove Row")
        btn_rem.setFixedWidth(90)
        btn_rem.clicked.connect(self.remove_row)

        
        footer_layout.addWidget(btn_up)
        footer_layout.addWidget(btn_down)
        footer_layout.addWidget(btn_add)
        footer_layout.addWidget(btn_rem)

        # Middle: Spacer
        footer_layout.addStretch()

        # Right: Apply && Close
        btn_apply = QPushButton("✅ Apply && Close")
        btn_apply.setFixedWidth(130)
        btn_apply.setFixedHeight(30)
        btn_apply.clicked.connect(self.accept) 

        footer_layout.addWidget(btn_apply)

        layout.addWidget(footer_group)
        self.setLayout(layout)

    def load_table_data(self):
        self.table.setRowCount(0)
        
        
        keys = list(self.mapping_data.keys()) 
        
        all_objects = [o.name for o in rt.objects]
        
        for row_idx, key in enumerate(keys):
            val = self.mapping_data[key]
            self.table.insertRow(row_idx)
            
            suffix = val.get("target_bone", key)
            param = val.get("param_name", "")
            pat = val.get("pattern", "")
            mode = val.get("mode", "PR")
            method = val.get("method", "DEFAULT")
            raw_matrix = val.get("matrix", [[1,0,0], [0,1,0], [0,0,1], [0,0,0]])

            self.table.setItem(row_idx, 0, QTableWidgetItem(key))
            self.table.setItem(row_idx, 1, QTableWidgetItem(suffix))
            self.table.setItem(row_idx, 2, QTableWidgetItem(param))
            self.table.setItem(row_idx, 3, QTableWidgetItem(pat))
            self.table.setItem(row_idx, 4, QTableWidgetItem(mode))
            self.table.setItem(row_idx, 5, QTableWidgetItem(method))
            
            mat_widget = MatrixCellWidget(raw_matrix, row_idx, self.on_vector_clicked)
            self.table.setCellWidget(row_idx, 6, mat_widget)
            
            # Check Status
            clean_pat = pat.replace("*", "")
            found = False
            if "*" in pat:
                import fnmatch
                found = any(fnmatch.fnmatch(o, pat) for o in all_objects)
            else:
                found = clean_pat in all_objects
                
            stat_item = QTableWidgetItem("FOUND" if found else "MISSING")
            stat_item.setForeground(QColor("#00FF00") if found else QColor("#FF5555"))
            self.table.setItem(row_idx, 7, stat_item)

    def get_full_json_data(self):
        new_map = {}
        for row in range(self.table.rowCount()):
            
            key_item = self.table.item(row, 0)
            if not key_item: continue
            key = key_item.text().strip()
            if not key: continue
            
            
            mat_widget = self.table.cellWidget(row, 6)
            
            
            new_map[key] = {
                "target_bone": self.table.item(row, 1).text().strip(),
                "param_name": self.table.item(row, 2).text().strip(),
                "pattern": self.table.item(row, 3).text().strip(),
                "mode": self.table.item(row, 4).text().strip(),
                "method": self.table.item(row, 5).text().strip(),
                "matrix": mat_widget.get_data() if mat_widget else []
            }
            
        self.full_data["mapping"] = new_map
        return self.full_data

    
    def on_vector_clicked(self, widget):
        
        if self.active_vector_widget and self.active_vector_widget != widget:
            try: 
                self.active_vector_widget.set_inactive()
            except: 
                pass
        
        
        self.active_vector_widget = widget
        
        
        self.table.selectRow(widget.parent_row)
        
        
        try:
            
            row_idx = widget.parent_row
            alias_item = self.table.item(row_idx, 0)
            alias_name = alias_item.text() if alias_item else "Unknown"
            
            
            vec_map = {
                1: "Row 1 (X Axis)", 
                2: "Row 2 (Y Axis)", 
                3: "Row 3 (Z Axis)", 
                4: "Position Offset"
            }
            vec_info = vec_map.get(widget.vec_index, "Unknown Vector")
            
            
            self.lbl_status.setText(f"SELECTED: {alias_name} -> {vec_info}")
            
            
            self.lbl_status.setStyleSheet("color: #00AAFF; font-weight: bold;")
            
        except Exception as e:
            self.lbl_status.setText(f"Error reading selection: {e}")

    def add_row(self):
        r = self.table.rowCount(); self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem("New_Key"))
        self.table.setItem(r, 1, QTableWidgetItem("Suffix"))
        self.table.setItem(r, 2, QTableWidgetItem("Param"))
        self.table.setItem(r, 3, QTableWidgetItem("*Pattern*"))
        self.table.setItem(r, 4, QTableWidgetItem("D"))
        self.table.setItem(r, 5, QTableWidgetItem("DEFAULT"))
        self.table.setCellWidget(r, 6, MatrixCellWidget([[1,0,0],[0,1,0],[0,0,1],[0,0,0]], r, self.on_vector_clicked))
        self.table.setItem(r, 7, QTableWidgetItem("-"))

    def remove_row(self):
        curr = self.table.currentRow()
        if curr >= 0: self.table.removeRow(curr)

    def move_row_up(self):
        row = self.table.currentRow()
        if row > 0:
            self.swap_rows(row, row - 1)
            self.table.selectRow(row - 1)

    def move_row_down(self):
        row = self.table.currentRow()
        if row < self.table.rowCount() - 1:
            self.swap_rows(row, row + 1)
            self.table.selectRow(row + 1)

    def get_row_content(self, row):
        
        data = {}
        
        for col in [0, 1, 2, 3, 4, 5, 7]:
            item = self.table.item(row, col)
            data[col] = {
                "text": item.text() if item else "",
                "fg": item.foreground() if item else QColor("white")
            }
        
        
        mat_widget = self.table.cellWidget(row, 6)
        if mat_widget:
            data[6] = mat_widget.get_data() 
        else:
            data[6] = [[1,0,0],[0,1,0],[0,0,1],[0,0,0]]
            
        return data

    def set_row_content(self, row, data):
        
        for col in [0, 1, 2, 3, 4, 5, 7]:
            item = QTableWidgetItem(data[col]["text"])
            item.setForeground(data[col]["fg"])
            self.table.setItem(row, col, item)
        
        
        matrix_data = data[6]
        mat_widget = MatrixCellWidget(matrix_data, row, self.on_vector_clicked)
        self.table.setCellWidget(row, 6, mat_widget)

    def swap_rows(self, r1, r2):
        
        d1 = self.get_row_content(r1)
        d2 = self.get_row_content(r2)
        
        
        self.set_row_content(r1, d2)
        self.set_row_content(r2, d1)
            
    def filter_table(self, text):
        search_text = text.lower()
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            match = item and search_text in item.text().lower()
            self.table.setRowHidden(r, not match)

    def rotate_active_vector(self, axis):
        if not self.active_vector_widget: return
        try:
            vec = rt.point3(*json.loads(self.active_vector_widget.text()))
            rot_tm = rt.matrix3(1)
            if axis == "x": rot_tm = rt.rotateXMatrix(90)
            elif axis == "y": rot_tm = rt.rotateYMatrix(90)
            elif axis == "z": rot_tm = rt.rotateZMatrix(90)
            new_vec = vec * rot_tm
            parent_cell = self.table.cellWidget(self.active_vector_widget.parent_row, 6)
            parent_cell.set_data_at_index(self.active_vector_widget.vec_index, new_vec)
        except: pass

    def save_to_json(self):
        
        self.get_full_json_data() 
        
        
        path, _ = QFileDialog.getSaveFileName(self, "Save Configuration", "", "JSON Files (*.json)")
        if path:
            try:
                
                json_str = json.dumps(self.full_data, indent=4)
                
                
                
                def compact_matrix_match(match):
                    
                    full_text = match.group(0)
                    
                    compacted = re.sub(r'\s+', '', full_text)
                    
                    compacted = compacted.replace(':', ': ')
                    return compacted

                
                json_str = re.sub(r'"matrix":\s*\[\s*\[.*?\]\s*\]', compact_matrix_match, json_str, flags=re.DOTALL)
                
                
                with open(path, 'w') as f:
                    f.write(json_str)
                
                QMessageBox.information(self, "Saved", f"Successfully saved (Compact Mode) to:\n{os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", str(e))

    def reset_active_vector(self):
        if not self.active_vector_widget: return
        idx = self.active_vector_widget.vec_index
        default = rt.point3(0,0,0)
        if idx == 1: default = rt.point3(1,0,0)
        elif idx == 2: default = rt.point3(0,1,0)
        elif idx == 3: default = rt.point3(0,0,1)
        parent_cell = self.table.cellWidget(self.active_vector_widget.parent_row, 6)
        parent_cell.set_data_at_index(idx, default)

    def launch_calibrator(self):
        self.calib_win = LiveCalibrator(self.main_ui, self)
        self.calib_win.show()

    def trigger_validate(self):
        self.get_full_json_data()
        self.main_ui.current_mapping = self.full_data["mapping"]
        self.main_ui.full_json_data = self.full_data 
        if hasattr(self.main_ui, "run_process"):
            self.main_ui.run_process()


class ValidationReportDialog(QDialog):
    def __init__(self, error_list, parent=None):
        super(ValidationReportDialog, self).__init__(parent)
        self.setWindowTitle("Validation Report")
        self.resize(700, 450)
        
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        
        self.error_list = error_list 
        self.selected_alias = None
        self.action = "cancel" 

        layout = QVBoxLayout()
        
        # Header
        header = QLabel(f"⚠️ Found {len(error_list)} Alignment Issues")
        header.setStyleSheet("color: #FF5555; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Bone Alias", "Error Detail", "Suggestion"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.table.setRowCount(len(error_list))
        for i, err in enumerate(error_list):
            self.table.setItem(i, 0, QTableWidgetItem(err['alias']))
            self.table.setItem(i, 1, QTableWidgetItem(err['msg']))
            self.table.setItem(i, 2, QTableWidgetItem(err['fix_text'])) 
            
            self.table.item(i, 0).setData(Qt.UserRole, err['alias'])

        self.table.doubleClicked.connect(self.fix_selected)
        layout.addWidget(self.table)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        
        
        btn_autofix = QPushButton("✨ Auto-Fix ALL Issues (Magic)")
        btn_autofix.setFixedHeight(45)
        btn_autofix.clicked.connect(self.do_autofix)
        
        btn_manual = QPushButton("🛠️ Fix Selected Manually")
        btn_manual.setFixedHeight(45)
        btn_manual.clicked.connect(self.fix_selected)
        
        btn_ignore = QPushButton("Build Anyway (Risky)")
        btn_ignore.setFixedHeight(45)
        btn_ignore.clicked.connect(self.do_build)

        btn_layout.addWidget(btn_autofix) 
        btn_layout.addWidget(btn_manual)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ignore)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    

    def fix_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            self.selected_alias = item.data(Qt.UserRole)
            self.action = "manual_fix"
            self.accept()
        else:
            QMessageBox.warning(self, "Select", "Please select a row first.")

    def do_autofix(self):
        
        self.action = "auto_fix"
        self.accept()

    def do_build(self):
        self.action = "build"
        self.accept()

    def on_double_click(self):
        self.fix_selected()


#------------------------------------
# About Dialog
#------------------------------------

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super(AboutDialog, self).__init__(parent)
        import constants, utils #
        self.setWindowTitle(f"About {constants.PRODUCT_NAME}") #
        self.setFixedSize(350, 250)
        
        layout = QVBoxLayout()
        
        
        title = QLabel(f"🚀 {constants.PRODUCT_NAME}") #
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00AAFF;")
        layout.addWidget(title)
        
        info = QLabel(f"Version: {constants.VERSION}\nAuthor: {constants.AUTHOR}\n\n"
                      "Advanced Auto-Rigging Tool for 3ds Max.") #
        layout.addWidget(info)
        
        layout.addStretch()
        
        
        h_btns = QHBoxLayout()
        btn_git = QPushButton("GitHub")
        btn_git.clicked.connect(lambda: utils.open_url(constants.GITHUB_URL)) #
        btn_git.setStyleSheet("""
            QPushButton {
                background-color: #333333; 
                color: #FFFFFF; 
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #555555; 
            }
        """)
        
        btn_pay = QPushButton("Support (PayPal)")
        #btn_pay.setStyleSheet("background-color: #0070ba; color: white;")
        btn_pay.clicked.connect(lambda: utils.open_url(constants.DONATION_LINK)) #

        btn_pay.setStyleSheet("""
            QPushButton {
                background-color: #FFC439; 
                color: #00457C; 
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #FFD46A;
            }
        """)
        
        h_btns.addWidget(btn_git)
        h_btns.addWidget(btn_pay)
        layout.addLayout(h_btns)
        
        self.setLayout(layout)