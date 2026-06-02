import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import math
from PIL import Image, ImageTk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# KD-Tree
class Node:
    def __init__(self, point, dimension, category, name):
        self.point = point
        self.dimension = dimension
        self.category = category
        self.name = name
        self.left = None
        self.right = None

class KDTree:
    def __init__(self, data):
        self.k = 3
        self.elevators = [r[0] for r in data if r[1] == "elevator"]
        self.root = self.construct(data.copy(), depth=0)
        self.nodes_list = [Node(r[0], 0, r[1], r[2]) for r in data]
    
    def best_dimension(self, data):
        best_dim   = 0
        best_spread = -1
        for dim in range(self.k):
            values = [row[0][dim] for row in data]
            spread = max(values) - min(values)
            if spread > best_spread:
                best_spread = spread
                best_dim    = dim
        return best_dim


    def construct(self, data, depth):
        if not data:
            return None
        dimension = self.best_dimension(data)
        self.data_sort(data, dimension)
        median = len(data) // 2
        point, category, name = data[median]
        new_node = Node(point, dimension, category, name)
        new_node.left  = self.construct(data[:median],       depth + 1)
        new_node.right = self.construct(data[median + 1:],   depth + 1)
        return new_node

    def data_sort(self, data, dimension):

        def partition(data, low, high):
            pivot     = low
            pivot_val = data[low][0][dimension]
            i, j = low + 1, high
            while i <= j:
                while i <= j and data[i][0][dimension] <= pivot_val: i += 1
                while i <= j and data[j][0][dimension] > pivot_val:  j -= 1
                if i <= j:
                    data[i], data[j] = data[j], data[i]
                    i += 1; j -= 1
            data[pivot], data[j] = data[j], data[pivot]
            return j

        def quick_sort(data, low, high):
            if low < high:
                pi = partition(data, low, high)
                quick_sort(data, low,   pi - 1)
                quick_sort(data, pi + 1, high)

        quick_sort(data, 0, len(data) - 1)

    def integrating_floors(self, p1, p2):
        if p1[2] == p2[2]:
            return 0
        floor_diff = abs(p1[2] - p2[2])
        if not self.elevators:
            return floor_diff * 100
        nearest_elevator_p1 = min(self.elevators, key=lambda e: (p1[0]-e[0])**2 + (p1[1]-e[1])**2)
        nearest_elevator_p2 = min(
            (e for e in self.elevators if e[2] == p2[2]),
            key=lambda e: (p2[0]-e[0])**2 + (p2[1]-e[1])**2,
            default=nearest_elevator_p1
        )
        dist_from_p1 = math.sqrt((p1[0]-nearest_elevator_p1[0])**2 + (p1[1]-nearest_elevator_p1[1])**2)
        dist_to_p2   = math.sqrt((p2[0]-nearest_elevator_p2[0])**2 + (p2[1]-nearest_elevator_p2[1])**2)
        return (dist_from_p1 + dist_to_p2) * floor_diff

    def get_distance(self, p1, p2):
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        horizontal    = dx**2 + dy**2
        vertical_cost = self.integrating_floors(p1, p2)
        return horizontal + vertical_cost**2

    def get_distance_broken_down(self, p1, p2):
        """Returns (horizontal_dist, floor_penalty, total_dist) as readable floats."""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        horizontal_dist = math.sqrt(dx**2 + dy**2)
        floor_penalty   = self.integrating_floors(p1, p2)
        total           = math.sqrt(horizontal_dist**2 + floor_penalty**2)
        return horizontal_dist, floor_penalty, total

    def find_nearest(self, point, place):
        return self.search(self.root, point, depth=0, best=None, place=place)

    def search(self, current_node, point, depth, best, place):
        if current_node is None:
            return best
        if point != current_node.point and current_node.category == place:
            if best is None or self.get_distance(point, current_node.point) < self.get_distance(point, best.point):
                best = current_node
        axis = current_node.dimension
        if point[axis] < current_node.point[axis]:
            next_branch, opposite_branch = current_node.left,  current_node.right
        else:
            next_branch, opposite_branch = current_node.right, current_node.left
        best = self.search(next_branch,    point, depth + 1, best, place)
        if best is None or (point[axis] - current_node.point[axis])**2 < self.get_distance(point, best.point):
            best = self.search(opposite_branch, point, depth + 1, best, place)
        return best


# App

class CampusMapApp3D:
    floor_image_paths = {
        -1: "maps/lg_floor.png",
        0: "maps/ground_floor.png",
        1: "maps/floor_1.png",
        2: "maps/floor_2.png",
        3: "maps/floor_3.png",
        4: "maps/floor_4.png",
    }

    def __init__(self, root, raw_data, categories):
        self.root = root
        self.root.title("Habib University Campus Navigator")
        self.root.geometry("1280x720")

        self.tree       = KDTree(raw_data)
        self.categories = sorted(categories)

        self.current_floor = 0
        self.floors        = [-1, 0, 1, 2, 3, 4]
        self.floor_labels  = {-1: "LG", 0: "G", 1: "1st floor", 2: "2nd floor", 3: "3rd floor", 4: "4th floor"}

        self.current_mode  = None
        self.search_result = None
        self.click_point   = None

        # Base coordinate space
        self.map_logical_width  = 350
        self.map_logical_height = 550

        # Base scale/offset
        self.scale    = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        # Zoom & pan on top of base scale
        self.zoom_level = 1.0
        self.pan_x      = 0.0
        self.pan_y      = 0.0
        self._drag_start = None   # for right-click pan
        
        self.floor_images_raw = {}
        self.floor_images_tk  = {}
        floor_image_paths = {
            -1: "maps/lg_floor.png",
            0: "maps/ground_floor.png",
            1: "maps/floor_1.png",
            2: "maps/floor_2.png",
            3: "maps/floor_3.png",
            4: "maps/floor_4.png",
        }

        for floor, path in floor_image_paths.items():
            self.floor_images_raw[floor] = Image.open(path).convert("RGBA")


        self.setup_ui()
        self.redraw_map()


    #UI setup
    def setup_ui(self):
        #Top control bar
        ctrl = ctk.CTkFrame(self.root, corner_radius=0, fg_color=("gray85", "gray15"))
        ctrl.pack(fill="x", side="top")

        ctk.CTkLabel(ctrl, text="Floor:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(20, 5), pady=12)
        self.floor_var = tk.IntVar(value=self.current_floor)
        for f in self.floors:
            ctk.CTkRadioButton(ctrl, text=self.floor_labels[f], variable=self.floor_var,
                               value=f, command=self.change_floor, width=55).pack(side="left", padx=4)

        self.lbl_status = ctk.CTkLabel(ctrl, text=" | VIEWING", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_status.pack(side="left", padx=15)

        #Right-side buttons
        ctk.CTkButton(ctrl, text="🔍 Find Nearest",
                      command=self.mode_search).pack(side="right", padx=15)
        ctk.CTkButton(ctrl, text="✖ Clear", command=self.clear_search,
                      fg_color="transparent", border_width=2,
                      text_color="white", width=80).pack(side="right", padx=5)
        ctk.CTkButton(ctrl, text="⟳ Reset View", command=self.reset_view,
                      fg_color="transparent", border_width=2,
                      text_color="white", width=100).pack(side="right", padx=5)

        #Canvas
        canvas_frame = ctk.CTkFrame(self.root, corner_radius=10)
        canvas_frame.pack(fill="both", expand=True, padx=20, pady=(10, 5))

        self.canvas = tk.Canvas(canvas_frame, bg="#1a1a1a", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)

        # Mouse bindings
        self.canvas.bind("<Button-1>",   self.on_canvas_click)  
        self.canvas.bind("<Button-3>",   self.on_pan_start)       
        self.canvas.bind("<B3-Motion>",  self.on_pan_drag)       
        self.canvas.bind("<MouseWheel>", self.on_zoom)           
        self.canvas.bind("<Button-4>",   self.on_zoom)           
        self.canvas.bind("<Button-5>",   self.on_zoom)           
        self.canvas.bind("<Configure>",  self.on_resize)

        #Bottom result bar
        result_bar = ctk.CTkFrame(self.root, corner_radius=0, fg_color=("gray80", "gray18"), height=40)
        result_bar.pack(fill="x", side="bottom")
        result_bar.pack_propagate(False)

        self.lbl_result = ctk.CTkLabel(
            result_bar,
            text="No search yet  ·  scroll to zoom  ·  right-click drag to pan",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        self.lbl_result.pack(side="left", padx=20)

    #coordinate helpers
    def _effective_scale(self):
        return self.scale * self.zoom_level

    def map_to_screen(self, lx, ly):
        s = self._effective_scale()
        return lx * s + self.offset_x + self.pan_x, ly * s + self.offset_y + self.pan_y

    def screen_to_map(self, sx, sy):
        s = self._effective_scale()
        return int((sx - self.offset_x - self.pan_x) / s), int((sy - self.offset_y - self.pan_y) / s)

    #resize
    def on_resize(self, event):
        scale_w = event.width  / self.map_logical_width
        scale_h = event.height / self.map_logical_height
        self.scale = min(scale_w, scale_h) * 0.95
        scaled_w   = self.map_logical_width  * self.scale
        scaled_h   = self.map_logical_height * self.scale
        self.offset_x = (event.width  - scaled_w) / 2
        self.offset_y = (event.height - scaled_h) / 2
        self.redraw_map()

    #zoom
    def on_zoom(self, event):
        #Determine zoom direction
        if event.num == 4 or (hasattr(event, "delta") and event.delta > 0):
            factor = 1.12
        else:
            factor = 1 / 1.12

        #Logical position under the mouse before zoom
        s = self._effective_scale()
        lx = (event.x - self.offset_x - self.pan_x) / s
        ly = (event.y - self.offset_y - self.pan_y) / s

        self.zoom_level = max(0.5, min(12.0, self.zoom_level * factor))

        #Adjusted pan
        s_new = self._effective_scale()
        self.pan_x = event.x - self.offset_x - lx * s_new
        self.pan_y = event.y - self.offset_y - ly * s_new

        self.redraw_map()

    #pan
    def on_pan_start(self, event):
        self._drag_start = (event.x, event.y, self.pan_x, self.pan_y)

    def on_pan_drag(self, event):
        if self._drag_start is None:
            return
        sx0, sy0, px0, py0 = self._drag_start
        self.pan_x = px0 + (event.x - sx0)
        self.pan_y = py0 + (event.y - sy0)
        self.redraw_map()

    #reset view
    def reset_view(self):
        self.zoom_level = 1.0
        self.pan_x      = 0.0
        self.pan_y      = 0.0
        self.redraw_map()

    #floor / mode
    def change_floor(self):
        self.current_floor = self.floor_var.get()
        self.redraw_map()

    def mode_search(self):
        self.current_mode = "SEARCH"
        self.lbl_status.configure(text=" | SEARCH — click a point on the map", text_color="#3498db")

    def clear_search(self):
        self.search_result = None
        self.click_point   = None
        self.current_mode  = None
        self.lbl_status.configure(text=" | VIEWING", text_color="white")
        self.lbl_result.configure(
            text="No search yet  ·  scroll to zoom  ·  right-click drag to pan",
            text_color="gray60"
        )
        self.redraw_map()

    #click search dialog
    def on_canvas_click(self, event):
        if self.current_mode != "SEARCH":
            return
        kd_x, kd_y    = self.screen_to_map(event.x, event.y)
        self.click_point = (kd_x, kd_y, self.current_floor)
        self.open_search_dialog()

    def open_search_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Find Nearest")
        dialog.geometry("300x210")
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="Select category to search:", font=ctk.CTkFont(weight="bold")).pack(pady=(20, 8))

        var_cat = ctk.StringVar(value=self.categories[0])
        ctk.CTkOptionMenu(dialog, variable=var_cat, values=self.categories, width=220).pack(pady=5)

        def do_search():
            target_category  = var_cat.get()
            self.search_result = self.tree.find_nearest(self.click_point, target_category)

            if self.search_result:
                res_point = self.search_result.point
                res_floor = res_point[2]
                h_dist, v_penalty, total = self.tree.get_distance_broken_down(self.click_point, res_point)

                # Switch floor if needed
                if res_floor != self.current_floor:
                    self.floor_var.set(res_floor)
                    self.current_floor = res_floor
                    messagebox.showinfo(
                        "Floor Switch",
                        f"Result is on {self.floor_labels.get(res_floor, res_floor)}. Switching floor."
                    )

                # Update result bar
                floor_tag = (
                    f"  ·  Floor penalty: {v_penalty:.1f} units"
                    if v_penalty > 0 else "  ·  Same floor"
                )
                self.lbl_result.configure(
                    text=(
                        f"📍 Nearest {target_category}: {self.search_result.name}"
                        f"  ·  Horizontal: {h_dist:.1f} units"
                        f"{floor_tag}"
                        f"  ·  Total distance: {total:.1f} units"
                    ),
                    text_color="#2ecc71"
                )
            else:
                self.lbl_result.configure(
                    text=f"No '{target_category}' found on any floor.",
                    text_color="#e74c3c"
                )

            self.current_mode = None
            self.lbl_status.configure(text=" | VIEWING", text_color="white")
            self.redraw_map()
            dialog.destroy()

        ctk.CTkButton(dialog, text="Search", command=do_search, width=160).pack(pady=20)

    #drawing
    def _draw_floor_image(self, bx0, by0, bx1, by1):
        img_pil = self.floor_images_raw.get(self.current_floor)
        if img_pil is None:
            self.canvas.create_rectangle(bx0, by0, bx1, by1,
                                        outline="#2a2a2a", fill="#111111")
            return

        w = max(1, int(bx1 - bx0))
        h = max(1, int(by1 - by0))

        resized = img_pil.resize((w, h), Image.LANCZOS)
        tk_img  = ImageTk.PhotoImage(resized)

        # MUST store on self — local var gets garbage collected → blank image
        self.floor_images_tk[self.current_floor] = tk_img

        self.canvas.create_image(bx0, by0, anchor="nw", image=tk_img)

    def redraw_map(self):
        self.canvas.delete("all")

        CATEGORY_COLORS = {
        "male prayer area":           "#003166",  
        "female prayer area":           "#820D38",
        "auditorium/hall":     "#76c0f1", 
        "recreation":    "#c33fe7",  
        "atm":                   "#00ff6a",  
        "transit point":"#8400ff", 
        "office":                "#e67e22",  
        "library":       "#e74c3c",  
        "faculty pods":          "#edb7ff",   
        "washroom":              "#345577",  
        "lab/studio/creatives":  "#53d455",
        "waiting":   "#95a5a6",  
        "cafeteria":             "#19c9ff", 
        "elevator":              "#f1c40f",
        "classroom":             "#015624",
    }

        #a faint boundary
        bx0, by0 = self.map_to_screen(0, 0)
        bx1, by1 = self.map_to_screen(self.map_logical_width-10, self.map_logical_height-10)
        self._draw_floor_image(bx0, by0, bx1, by1)

        #nodes on the current floor
        s = self._effective_scale()
        #Scale dot and font
        dot_r     = max(4, min(10, int(6  * self.zoom_level)))
        font_size = max(7, min(14, int(9  * self.zoom_level)))
        #if zoom is reasonable
        show_labels = self.zoom_level >= 0.9

        for nd in self.tree.nodes_list:
            if nd.point[2] != self.current_floor:
                continue

            sx, sy = self.map_to_screen(nd.point[0], nd.point[1])
            color  = CATEGORY_COLORS.get(nd.category)

            self.canvas.create_oval(sx-dot_r, sy-dot_r, sx+dot_r, sy+dot_r,
                                    fill=color, outline="#000000", width=1)

            if show_labels and nd.category != "elevator":
                self.canvas.create_text(sx, sy + dot_r + 5,
                                        text=nd.name, fill="white",
                                        font=("Arial", font_size),
                                        anchor="n")

        #Draw click origin
        if self.click_point and self.click_point[2] == self.current_floor:
            cx, cy = self.map_to_screen(self.click_point[0], self.click_point[1])
            self.canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill="#f39c12", outline="white")
            self.canvas.create_text(cx, cy-14, text="YOU", fill="#f39c12",
                                    font=("Arial", 9, "bold"))

        #Draw line from origin to result
        if (self.search_result and self.click_point
                and self.search_result.point[2] == self.current_floor
                and self.click_point[2] == self.current_floor):
            cx, cy = self.map_to_screen(self.click_point[0],       self.click_point[1])
            tx, ty = self.map_to_screen(self.search_result.point[0], self.search_result.point[1])
            self.canvas.create_line(cx, cy, tx, ty, fill="#e74c3c", width=2, dash=(6, 4))

        #Draw search result ping
        if self.search_result and self.search_result.point[2] == self.current_floor:
            tx, ty = self.map_to_screen(self.search_result.point[0], self.search_result.point[1])
            r_outer = dot_r + 8
            self.canvas.create_oval(tx-r_outer, ty-r_outer, tx+r_outer, ty+r_outer,
                                    outline="#e74c3c", width=3)
            self.canvas.create_oval(tx-dot_r, ty-dot_r, tx+dot_r, ty+dot_r, fill="#e74c3c")
            self.canvas.create_text(tx, ty - r_outer - 8,
                                    text=f"▶ {self.search_result.name}",
                                    fill="#e74c3c", font=("Arial", 11, "bold"), anchor="s")

        #Zoom level hint
        cw = self.canvas.winfo_width()
        self.canvas.create_text(cw - 10, 10,
                                text=f"zoom {self.zoom_level:.1f}×",
                                fill="gray40", font=("Arial", 9), anchor="ne")
        self.draw_color_bar()
    
    def draw_color_bar(self):
        CATEGORY_COLORS = {
            "male prayer area":           "#003166",  
            "female prayer area":           "#820D38",
            "auditorium/hall":     "#76c0f1", 
            "recreation":    "#c33fe7",  
            "atm":                   "#00ff6a",  
            "transit point":"#8400ff", 
            "office":                "#e67e22",  
            "library":       "#e74c3c",  
            "faculty pods":          "#edb7ff",   
            "washroom":              "#345577",  
            "lab/studio/creatives":  "#53d455",
            "waiting":   "#95a5a6",  
            "cafeteria":             "#19c9ff", 
            "elevator":              "#f1c40f",
            "classroom":             "#015624",
        }
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        row_h     = 20
        pad       = 10
        dot_r     = 5
        font_size = 9
        box_w     = 180
        box_h     = pad * 2 + row_h * len(CATEGORY_COLORS)

        x0 = cw - box_w - 10
        y0 = ch - box_h - 10
        x1 = cw - 10
        y1 = ch - 10


        self.canvas.create_rectangle(x0, y0, x1, y1,
                                    fill="#1a1a1a", outline="#3a3a3a",
                                    width=1, tags="legend")


        self.canvas.create_text(x0 + box_w // 2, y0 + pad,
                                text="REFERENCE\n", fill="gray60",
                                font=("Arial", 9, "bold"),
                                anchor="n", tags="legend")


        for i, (cat, color) in enumerate(CATEGORY_COLORS.items()):
            row_y = y0 + pad + row_h + i * row_h

            self.canvas.create_oval(
                x0 + pad - dot_r,       row_y - dot_r,
                x0 + pad + dot_r,       row_y + dot_r,
                fill=color, outline="", tags="legend"
            )
            self.canvas.create_text(
                x0 + pad * 2 + dot_r, row_y,
                text=cat.capitalize(),
                fill="gray80",
                font=("Arial", font_size),
                anchor="w", tags="legend"
            )


# entry point
def data_reader(filepath):
    campus_data = []
    categories  = []
    with open(filepath, newline="") as f:
        for line in f.readlines():
            if not line.strip():
                continue
            d = line.split(",")
            r = ((int(d[0]), int(d[1]), int(d[2])), d[3], d[4].strip())
            campus_data.append(r)
            categories.append(d[3])
            
    return campus_data, list(set(categories))


if __name__ == "__main__":
    raw_data, categories = data_reader("campus_data.csv")
    root = ctk.CTk()
    app  = CampusMapApp3D(root, raw_data, categories)
    root.mainloop()
