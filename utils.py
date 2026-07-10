from PySide6.QtCore import QObject, Signal
import pymxs
import os
import webbrowser
rt = pymxs.runtime

# ---------------------------------------------------------------------------
# LOGGER SYSTEM
# ---------------------------------------------------------------------------
class QLogger(QObject):
    sig_log = Signal(str, str)

    def info(self, msg, color="#00FF00"): 
        
        self.sig_log.emit(f"[INFO]: {msg}", color)

    def warning(self, msg, color="#FFA500"): 
        self.sig_log.emit(f"[WARN]: {msg}", color)

    def error(self, msg, color="#FF0000"): 
        self.sig_log.emit(f"[ERROR]: {msg}", color)

# ---------------------------------------------------------------------------
# About
# ---------------------------------------------------------------------------
def open_url(url):
    
    webbrowser.open(url)

# ---------------------------------------------------------------------------
# HELPERS: PYTHON BVH PARSER (NATIVE)
# ---------------------------------------------------------------------------
class SimpleBVHImporter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.nodes = {} 
        self.motion_data = []
        self.frame_time = 0.033333
        self.root_name = None
        self.channel_map = []

    def parse(self):
        with open(self.file_path, 'r') as f:
            content = f.read().split()
        
        iterator = iter(content)
        current_node = None
        node_stack = []
        mode = "HIERARCHY"
        
        try:
            while True:
                token = next(iterator)
                
                if token == "HIERARCHY": continue
                elif token == "ROOT" or token == "JOINT":
                    name = next(iterator)
                    self.nodes[name] = {"children": [], "channels": [], "offset": [0,0,0], "order": ""}
                    if token == "ROOT": self.root_name = name
                    
                    if node_stack:
                        parent = node_stack[-1]
                        self.nodes[parent]["children"].append(name)
                        self.nodes[name]["parent"] = parent
                    else:
                        self.nodes[name]["parent"] = None
                        
                    node_stack.append(name)
                    current_node = name
                    
                elif token == "End":
                    # End Site (Nub)
                    next(iterator) # Site
                    node_stack.append("EndSite") # Placeholder to pop later
                    
                elif token == "OFFSET":
                    if node_stack[-1] == "EndSite":
                        # Skip End Site Offset
                        next(iterator); next(iterator); next(iterator)
                    else:
                        x = float(next(iterator))
                        y = float(next(iterator))
                        z = float(next(iterator))
                        self.nodes[current_node]["offset"] = [x, y, z]
                        
                elif token == "CHANNELS":
                    count = int(next(iterator))
                    channels = []
                    for _ in range(count):
                        ch = next(iterator)
                        channels.append(ch)
                        self.channel_map.append((current_node, ch))
                    self.nodes[current_node]["channels"] = channels
                    
                elif token == "}":
                    node_stack.pop()
                    if node_stack: current_node = node_stack[-1]
                    
                elif token == "MOTION":
                    mode = "MOTION"
                    break
            
            # Parse Motion Header
            while True:
                token = next(iterator)
                if token == "Frames:": 
                    frames = int(next(iterator))
                elif token == "Frame": 
                    next(iterator) # Time:
                    self.frame_time = float(next(iterator))
                    break
            
            # Parse Motion Data
            
            data_values = list(iterator)
            
            total_channels = len(self.channel_map)
            
            # Chunking data per frame
            for i in range(0, len(data_values), total_channels):
                frame_chunk = data_values[i : i + total_channels]
                if len(frame_chunk) == total_channels:
                    self.motion_data.append([float(x) for x in frame_chunk])
                    
        except StopIteration:
            pass

    
    def build_in_max(self, target_height=None, logger=None):
        if not self.root_name: return []

        # BVH is Y-up. Height is measured along Y (offset[1]) in the spine chain.
        bvh_height = 0
        curr = self.root_name
        while curr and self.nodes[curr]["children"]:
            bvh_height += abs(self.nodes[curr]["offset"][1])
            curr = self.nodes[curr]["children"][0]

        scale_val = 1.0
        if target_height and bvh_height > 0:
            scale_val = target_height / bvh_height
            if logger: logger.info(f"Scale: {round(scale_val,3)} (BVH Height: {bvh_height})", "#00AAFF")

        # BVH Y-up, Z-forward  →  3ds Max Z-up, Y-forward
        # Remap: Max.X = BVH.X,  Max.Y = -BVH.Z,  Max.Z = BVH.Y
        def remap(bx, by, bz, s=1.0):
            return rt.point3(bx * s, -bz * s, by * s)

        created_nodes = {}
        all_created = []

        container = rt.Point(size=10, box=False, cross=True, wirecolor=rt.color(255, 255, 255))
        container.name = f"BVH_WORLD_{os.path.basename(self.file_path)}"
        container.pos = rt.point3(0, 0, 0)
        # No container rotation — axis remap is done explicitly per bone below.

        def create_rec(name, parent_obj):
            data = self.nodes[name]
            ox, oy, oz = data["offset"]
            world_pos = remap(ox, oy, oz, scale_val)

            p = rt.Point(size=2.0 * scale_val, box=True, wirecolor=rt.color(0, 255, 0), name=f"BVH_{name}")
            p.parent = parent_obj
            if parent_obj:
                p.transform = rt.transMatrix(world_pos) * parent_obj.transform
            else:
                p.pos = world_pos

            created_nodes[name] = p
            all_created.append(p)
            for child in data["children"]:
                create_rec(child, p)

        create_rec(self.root_name, container)

        rt.disableSceneRedraw()
        try:
            total_frames = len(self.motion_data)
            fps = 1.0 / self.frame_time
            rt.frameRate = fps
            ticks_per_frame = 4800 / fps
            rt.animationRange = rt.interval(0, int(total_frames * ticks_per_frame))

            with pymxs.animate(True):
                for f, frame_data in enumerate(self.motion_data):
                    rt.sliderTime = f

                    frame_map = {}
                    for i, val in enumerate(frame_data):
                        bone_name, ch = self.channel_map[i]
                        if bone_name not in frame_map: frame_map[bone_name] = {}
                        frame_map[bone_name][ch] = val

                    for name, channels in frame_map.items():
                        node = created_nodes.get(name)
                        if not node: continue

                        # Build rotation matrix respecting the channel order declared in BVH.
                        # BVH Euler rotations are applied in the order listed in the CHANNELS line.
                        # After building in BVH space, remap axes to Max space.
                        rot_tm = rt.matrix3(1)
                        for ch in self.nodes[name]["channels"]:
                            if "rotation" not in ch: continue
                            val = channels.get(ch, 0)
                            if   "Xrotation" in ch: rot_tm = rt.rotateXMatrix(val) * rot_tm
                            elif "Yrotation" in ch: rot_tm = rt.rotateZMatrix(val) * rot_tm   # BVH Y → Max Z
                            elif "Zrotation" in ch: rot_tm = rt.rotateYMatrix(-val) * rot_tm  # BVH Z → Max -Y

                        if "Xposition" in channels:
                            bx = channels.get("Xposition", 0)
                            by = channels.get("Yposition", 0)
                            bz = channels.get("Zposition", 0)
                            pos = remap(bx, by, bz, scale_val)
                        else:
                            ox, oy, oz = self.nodes[name]["offset"]
                            pos = remap(ox, oy, oz, scale_val)

                        local_tm = rot_tm * rt.transMatrix(pos)
                        if node.parent:
                            node.transform = local_tm * node.parent.transform

        finally:
            rt.enableSceneRedraw()
        return all_created


