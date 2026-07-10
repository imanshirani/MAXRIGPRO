import json
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QMenu, QApplication
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Signal



#---------------------------------------------------------------------------
# 1. MAPPING EDITOR WIDGETS (UPDATED WITH COPY/PASTE)
# ---------------------------------------------------------------------------

class ClickableVector(QLineEdit):
    focus_gained = Signal(object) 

    def __init__(self, text, vec_index, parent_row, parent_widget=None):
        super().__init__(text, parent_widget)
        self.vec_index = vec_index 
        self.parent_row = parent_row
        self.setReadOnly(True) 
        # فعال کردن منوی راست کلیک سفارشی
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def focusInEvent(self, event):
        self.setStyleSheet("background-color: #0078d7; color: white;") 
        self.focus_gained.emit(self)
        super().focusInEvent(event)

    def set_inactive(self):
        self.setStyleSheet("")

    def show_context_menu(self, pos):
        menu = QMenu(self)
        
        # --- Actions ---
        action_copy_vec = QAction("Copy This Vector ([x,y,z])", self)
        action_paste_vec = QAction("Paste Vector", self)
        
        menu.addSeparator()
        
        action_copy_matrix = QAction("📋 Copy WHOLE Matrix (4 Rows)", self)
        action_paste_matrix = QAction("💾 Paste WHOLE Matrix", self)
        
        # --- Connect ---
        action_copy_vec.triggered.connect(self.copy_vector)
        action_paste_vec.triggered.connect(self.paste_vector)
        action_copy_matrix.triggered.connect(self.copy_full_matrix)
        action_paste_matrix.triggered.connect(self.paste_full_matrix)
        
        # Add to menu
        menu.addAction(action_copy_vec)
        menu.addAction(action_paste_vec)
        menu.addSeparator()
        menu.addAction(action_copy_matrix)
        menu.addAction(action_paste_matrix)
        
        menu.exec(self.mapToGlobal(pos))

    # --- Logic ---
    def copy_vector(self):
        QApplication.clipboard().setText(self.text())

    def paste_vector(self):
        text = QApplication.clipboard().text()
        # اعتبارسنجی ساده: آیا فرمت شبیه لیست است؟
        if text.startswith("[") and text.endswith("]"):
            self.setText(text)
            # تریگر کردن آپدیت در دیتابیس اصلی (از طریق سیگنال فوکوس)
            self.focus_gained.emit(self)

    def copy_full_matrix(self):
        # دسترسی به ویجت پدر (MatrixCellWidget) برای گرفتن کل دیتا
        parent = self.parent()
        if hasattr(parent, "get_data_string"):
            full_data = parent.get_data_string()
            QApplication.clipboard().setText(full_data)

    def paste_full_matrix(self):
        text = QApplication.clipboard().text()
        parent = self.parent()
        if hasattr(parent, "set_full_data_from_string"):
            success = parent.set_full_data_from_string(text)
            if success:
                self.focus_gained.emit(self)


# --- ابزارک کلی که داخل سلول جدول قرار می‌گیرد (شامل ۴ باکس زیر هم) ---
class MatrixCellWidget(QWidget):
    def __init__(self, matrix_data, row_idx, callback_fn, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout() 
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2) 
        
        self.inputs = []
        
        if len(matrix_data) < 4: 
            matrix_data = [[1,0,0], [0,1,0], [0,0,1], [0,0,0]]
            
        def clean_number(n):
            if abs(n - round(n)) < 0.001: return int(round(n))
            return round(n, 4)

        def fmt_row(row_data):
            cleaned = [clean_number(x) for x in row_data]
            return json.dumps(cleaned).replace(" ", "")
        
        for i in range(4):
            val_str = fmt_row(matrix_data[i])
            # نکته مهم: self را به عنوان parent می‌فرستیم تا ClickableVector به آن دسترسی داشته باشد
            inp = ClickableVector(val_str, i+1, row_idx, parent_widget=self) 
            inp.focus_gained.connect(callback_fn)
            layout.addWidget(inp)
            self.inputs.append(inp)
            
        self.setLayout(layout)
        
    def get_data(self):
        res = []
        for inp in self.inputs:
            try: 
                val = json.loads(inp.text())
                res.append(val)
            except: 
                res.append([0,0,0])
        return res
    
    
    
    # --- تابع جدید برای کپی کل ماتریس ---
    def get_data_string(self):
        return json.dumps(self.get_data())

    # --- تابع جدید برای پیست کل ماتریس ---
    def set_full_data_from_string(self, json_str):
        try:
            data = json.loads(json_str)
            # بررسی اینکه آیا لیست لیست‌هاست
            if isinstance(data, list) and len(data) >= 3:
                for i, row_val in enumerate(data):
                    if i < 4:
                        # فرمت کردن تمیز
                        clean_str = json.dumps(row_val).replace(" ", "")
                        self.inputs[i].setText(clean_str)
                return True
        except:
            pass
        return False

    def set_data_at_index(self, idx, new_vec_point3):
        def clean_number(n):
            if abs(n - round(n)) < 0.001: return int(round(n))
            return round(n, 4)

        cleaned_list = [
            clean_number(new_vec_point3.x), 
            clean_number(new_vec_point3.y), 
            clean_number(new_vec_point3.z)
        ]
        final_str = json.dumps(cleaned_list).replace(" ", "")
        self.inputs[idx-1].setText(final_str)
        
    
        
    
