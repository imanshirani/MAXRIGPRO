import sys
import os
from PySide6 import QtWidgets, QtCore
import importlib
import pymxs
import gc


if "_maxrig_pro_dock" not in globals():
    _maxrig_pro_dock = None

def hard_cleanup():
    global _maxrig_pro_dock
    print("\n--- 🧹 Starting Cleanup Sequence: MAXRIG PRO ---")
    if _maxrig_pro_dock:
        try:
            _maxrig_pro_dock.close()
            _maxrig_pro_dock.deleteLater()
        except Exception as e:
            print(f"   - Warning during UI close: {e}")
        _maxrig_pro_dock = None
    gc.collect()
    print("--- ✅ Cleanup Complete ---\n")

def launch_maxrig_pro():
    global _maxrig_pro_dock
    hard_cleanup()

    
    rt = pymxs.runtime
    max_hwnd = rt.windows.getMAXHWND()
    main_window = QtWidgets.QWidget.find(max_hwnd)

    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir in sys.path:
        sys.path.remove(script_dir)
        
    sys.path.insert(0, script_dir)

    
    try:
        # پاک کردن کش ماژول‌های هم‌نام برای جلوگیری از تداخل با Kitbash
        for mod in ['constants', 'core', 'utils', 'widgets']:
            if mod in sys.modules:
                del sys.modules[mod]

        import constants, utils, widgets, dialogs, core, Cat_core
        importlib.reload(constants)
        importlib.reload(utils)   
        importlib.reload(widgets)
        importlib.reload(dialogs)
        importlib.reload(Cat_core)
        importlib.reload(core)  
    except Exception as e:
        print(f"❌ Error during module reload: {e}")
        return

    
    dock_ptr = QtWidgets.QDockWidget(constants.PRODUCT_NAME, main_window)
    dock_ptr.setObjectName("MAXRIG_PRO_DockWidget")
    dock_ptr.setFeatures(
        QtWidgets.QDockWidget.DockWidgetClosable | 
        QtWidgets.QDockWidget.DockWidgetMovable | 
        QtWidgets.QDockWidget.DockWidgetFloatable
    )
    dock_ptr.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)

    
    main_widget = core.AutoRIGG_UI()
    dock_ptr.setWidget(main_widget)

    
    main_window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock_ptr)
    
    dock_ptr.show()
    _maxrig_pro_dock = dock_ptr
    
    print(f"✅ {constants.PRODUCT_NAME} v{constants.VERSION} Launched.")

if __name__ == "__main__":
    launch_maxrig_pro()