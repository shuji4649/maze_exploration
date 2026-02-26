from tkinter import *
import os
import json
from typing import Optional, Type

from ..core.data_models import JsonMapData, JsonMapDataTile, JsonMapDataCell
from ..core.direction import Direction
from ..simulation.field import Field
from ..simulation.robot_interface import RobotInterface
from ..algorithms.strategies import ExplorationStrategy, ReferenceRightHandStrategy, DynamicDijkstraStrategy, DynamicDijkstraIncludeDistanceFromStartStrategy
from ..algorithms.mapping import MappingField

class MapViewer:
    def __init__(self):
        self.map_scale = 0.6
        self.root = Tk()
        self.root.title("Map Viewer")
        self.root.geometry("800x1200") # Increased height

        TitleLabel = Label(self.root, text="Map Viewer", font=("Helvetica", 10, "bold"))
        TitleLabel.pack(pady=10)
        
        self.packMapSelector()
        
        self.canvas = Canvas(self.root, width=int(800*0.8), height=int(800*0.8), bg="white")
        self.canvas.pack()
        
        self.small_cell_size = int(15 * self.map_scale)
        self.big_cell_size = int(45 * self.map_scale)

        self.fieldData: Optional[Field] = None
        self.robot: Optional[RobotInterface] = None
        self.strategy: Optional[ExplorationStrategy] = None
        self.is_running = False

        self.packButtons()
        
        # Load default map if exists
        # We need to find where maps are. 
        # In original code: "maps/" folder relative to cwd.
        if os.path.exists("maps"):
             files = [f for f in os.listdir("maps") if f.endswith(".json")]
             if files:
                 self.selected_map.set(os.path.join("maps", files[0]))
                 self.load_map_from_file(os.path.join("maps", files[0]))

    def start(self):
        self.root.mainloop()

    def packMapSelector(self):
        self.selected_map = StringVar()
        # Find maps
        map_files = []
        if os.path.exists("maps"):
             map_files = [os.path.join("maps", f) for f in os.listdir("maps") if f.endswith(".json")]
        
        if not map_files:
            map_files = ["No maps found"]
            
        self.selected_map.set(map_files[0])
        
        # OptionMenu behavior with dynamic list is tricky in Tkinter, 
        # but we can try to refresh it or just list what's available at start.
        map_dropdown = OptionMenu(self.root, self.selected_map, *map_files, command=self.load_map_from_file)
        map_dropdown.pack(pady=10)

    def load_map_from_file(self, file_path):
        if not os.path.exists(file_path):
            return
            
        with open(file_path, "r") as f:
            json_data = json.load(f)
            
        self.fieldData = Field("loaded_map")
        self.fieldData.readJson(json_data)
        self.draw_from_field(self.fieldData)

    def draw_from_field(self, fieldData: Field):
        self.fieldData = fieldData
        self.canvas.delete("all")
        
        # mapData is [y][x]
        # But we need to iterate rows (y) and cols (x)
        # mapData size is (2*length+1) rows, (2*width+1) cols
        
        if not self.fieldData.mapData:
            return

        rows = len(self.fieldData.mapData)
        cols = len(self.fieldData.mapData[0])

        for i in range(rows):
            for j in range(cols):
                # i is y, j is x
                cell = self.fieldData.mapData[i][j]
                
                # Canvas coords
                # Using logic from original:
                # x0 = (j//2)*(small + big) + small*(j%2)
                
                x0 = (j//2)*(self.small_cell_size+self.big_cell_size) + self.small_cell_size * (j % 2)
                y0 = (i//2)*(self.small_cell_size+self.big_cell_size) + self.small_cell_size * (i % 2)
                
                x1 = x0 + (self.big_cell_size if (j % 2 == 1) else self.small_cell_size)
                y1 = y0 + (self.big_cell_size if (i % 2 == 1) else self.small_cell_size)
                
                color = self.get_color(cell)
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="black", tag=f"cell_{i}_{j}") # Tag uses y, x
                
                if cell == 3: # Start
                    self.canvas.create_text((x0+x1)//2, (y0+y1)//2, text="S", fill="blue", font=("Helvetica", int(16*self.map_scale), "bold"))
        
        # Draw Robot at start
        if self.fieldData.jsonMapData.startTile:
             self.draw_robot_at(self.fieldData.jsonMapData.startTile.x, self.fieldData.jsonMapData.startTile.y, Direction.NORTH)

    def get_color(self, cell_value):
        if cell_value == 0: return "#FCFCFC"
        elif cell_value == 1: return "#000000"
        elif cell_value == 2: return "#FFFFFF"
        elif cell_value == 3: return "#FFFFFF" # Start is tile
        elif cell_value == 4: return "#0048FF" # Swamp
        else: return "#FF0000"

    def convertTileToCanvasCoords(self, tile_x, tile_y):
        # tile_x is column index (0..width-1)
        # tile_y is row index (0..length-1)
        
        # MapData index for center of tile:
        # x_idx = tile_x * 2 + 1
        # y_idx = tile_y * 2 + 1
        
        # Canvas X for x_idx:
        # (x_idx // 2) * (small+big) + small * (x_idx%2)
        # = tile_x * (small+big) + small
        
        # Center of that cell:
        # x_start = tile_x * (small+big) + small
        # width = big
        # center = x_start + big/2
        
        canvas_x = tile_x * (self.small_cell_size + self.big_cell_size) + self.small_cell_size + self.big_cell_size/2
        canvas_y = tile_y * (self.small_cell_size + self.big_cell_size) + self.small_cell_size + self.big_cell_size/2
        
        return canvas_x, canvas_y

    def draw_robot(self):
        if not self.robot: return
        self.draw_robot_at(self.robot.position[0], self.robot.position[1], self.robot.direction)

    def draw_robot_at(self, tx, ty, direction: Direction):
        self.canvas.delete("robot")
        cx, cy = self.convertTileToCanvasCoords(tx, ty)
        
        r = 15 * self.map_scale
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="red", width=2, tag="robot", fill="red")
        
        # Direction indicator (eyes)
        # Offset for eyes based on direction
        # NORTH (90): y-
        # SOUTH (270): y+
        # EAST (0): x+
        # WEST (180): x-
        
        eye_offset = 14 * self.map_scale
        eye_spacing = 8 * self.map_scale
        eye_r = 4 * self.map_scale
        
        # This logic is purely visual, can be simplified or copied.
        # Copying simplified logic
        dx, dy = Direction.get_dx_dy(direction)
        # dx, dy tells us where "forward" is. 
        # If North (0, -1): eyes are at cy - offset. Spaced by x.
        
        # To handle rotation easily, we can define left/right eyes relative to center
        # But stick to original if possible.
        # Original code used hardcoded per direction.
        
        ex1, ey1, ex2, ey2 = 0, 0, 0, 0
        
        if direction == Direction.NORTH:
            ex1, ey1 = cx - eye_spacing, cy - eye_offset
            ex2, ey2 = cx + eye_spacing, cy - eye_offset
        elif direction == Direction.SOUTH:
            ex1, ey1 = cx - eye_spacing, cy + eye_offset
            ex2, ey2 = cx + eye_spacing, cy + eye_offset
        elif direction == Direction.EAST:
            ex1, ey1 = cx + eye_offset, cy - eye_spacing
            ex2, ey2 = cx + eye_offset, cy + eye_spacing
        elif direction == Direction.WEST:
            ex1, ey1 = cx - eye_offset, cy - eye_spacing
            ex2, ey2 = cx - eye_offset, cy + eye_spacing
            
        self.canvas.create_oval(ex1-eye_r, ey1-eye_r, ex1+eye_r, ey1+eye_r, outline="black", width=2, tag="robot", fill="black")
        self.canvas.create_oval(ex2-eye_r, ey2-eye_r, ex2+eye_r, ey2+eye_r, outline="black", width=2, tag="robot", fill="black")

    def on_robot_move(self):
        self.draw_robot()
        self.canvas.update()
        self.canvas.after(30) # Delay for animation

    def on_robot_turn(self, angle):
        self.draw_robot()
        self.canvas.update()
        self.canvas.after(20)

    def on_map_update(self):
        # Redraw overlays (tile counts, wall counts)
        self.draw_overlays()

    def draw_overlays(self):
        if not self.strategy or not hasattr(self.strategy, 'mapping'): return
        
        mapping_field = self.strategy.mapping.mappingField
        
        self.canvas.delete("overlay") # clean old overlay
        
        # Iterate over all tiles in mapping
        for field_coord, info in mapping_field.mapData.items():
            if hasattr(info, 'visitTileCount'): # It's a tile
                # Tile Count
                if self.showTileCountToggle.get():
                     tx, ty = info.tileCoord
                     cx, cy = self.convertTileToCanvasCoords(tx, ty)
                     self.canvas.create_text(cx, cy, text=str(info.visitTileCount), fill="green", font=("Helvetica", int(12 * self.map_scale), "bold"), tag="overlay")
                
                # Wall Counts
                if self.showWallCountToggle.get():
                     tx, ty = info.tileCoord
                     cx, cy = self.convertTileToCanvasCoords(tx, ty)
                     
                     for d_int, count in info.visitWallCount.items():
                         if count > 0:
                             d = Direction(d_int)
                             dx, dy = Direction.get_dx_dy(d)
                             # Draw number slightly offset
                             offset = 20 * self.map_scale
                             wx, wy = cx + dx*offset, cy + dy*offset
                             self.canvas.create_text(wx, wy, text=str(count), fill="blue", font=("Helvetica", int(12 * self.map_scale), "bold"), tag="overlay")

    def run_robot(self, strategy_cls: Type[ExplorationStrategy], **kwargs):
        if self.is_running: return
        if not self.fieldData: return
        
        self.is_running = True
        
        # Init Robot
        self.robot = RobotInterface(self.fieldData, move_hook=self.on_robot_move, turn_hook=self.on_robot_turn)
        
        # Init Strategy
        self.strategy = strategy_cls(self.robot, on_update_map=self.on_map_update, **kwargs)
        
        self.update_status(f"Running {strategy_cls.__name__}...")
        
        # Start Loop
        self.root.after(100, self.step_strategy)

    def step_strategy(self):
        if not self.is_running: return
        
        finished = self.strategy.execute_step()
        
        if finished:
            self.is_running = False
            self.update_status(f"Completed! Cost: {self.robot.run_cost}")
            print(f"Exploration completed. Total cost: {self.robot.run_cost}")
        else:
            self.root.after(10, self.step_strategy)

    def stop_robot(self):
        self.is_running = False
        self.update_status("Stopped.")

    def update_status(self, text):
        self.canvas.delete("status")
        self.canvas.create_text(int(400*self.map_scale), int(650*self.map_scale), text=text, fill="red", font=("Helvetica", int(16*self.map_scale), "bold"), tag="status")


    def run_dijkstra_with_k(self):
        k = self.k_value.get()
        self.run_robot(DynamicDijkstraIncludeDistanceFromStartStrategy, k=k)

    def packButtons(self):
        frame = Frame(self.root)
        frame.pack(pady=10)
        
        Button(frame, text="Run Proposed (Dijkstra)", command=lambda: self.run_robot(DynamicDijkstraStrategy)).pack(side=LEFT, padx=5)
        Button(frame, text="Run Legacy (RightHand)", command=lambda: self.run_robot(ReferenceRightHandStrategy)).pack(side=LEFT, padx=5)
        Button(frame, text="Stop", command=self.stop_robot).pack(side=LEFT, padx=5)

        # Dijkstra + Distance from Start with k value
        k_frame = Frame(self.root)
        k_frame.pack(pady=5)

        Label(k_frame, text="k value:").pack(side=LEFT, padx=(0, 5))
        self.k_value = DoubleVar(value=0.2)
        self.k_scale = Scale(k_frame, from_=0.0, to=2.0, resolution=0.1, orient=HORIZONTAL, variable=self.k_value, length=200)
        self.k_scale.pack(side=LEFT, padx=5)
        Button(k_frame, text="Run Dijkstra + Distance (k)", command=self.run_dijkstra_with_k).pack(side=LEFT, padx=5)

        # Toggles
        self.showTileCountToggle = BooleanVar(value=True)
        Checkbutton(self.root, text="Show Tile Count", variable=self.showTileCountToggle, command=self.draw_overlays).pack()
        
        self.showWallCountToggle = BooleanVar(value=True)
        Checkbutton(self.root, text="Show Wall Count", variable=self.showWallCountToggle, command=self.draw_overlays).pack()

if __name__ == "__main__":
    app = MapViewer()
    app.start()
