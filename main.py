import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from tkinter import *
from tkinter import ttk


@dataclass
class JsonMapDataTilePosition:
    x: int
    y: int
    z: int


@dataclass
class JsonMapDataTile:
    changeFloorTo: Optional[int] = None
    victims: Optional[Dict[str, str]] = None


@dataclass
class JsonMapDataCell:
    isWall: bool = False
    halfWall: Optional[int] = None
    isTile: bool = False
    tile: Optional[JsonMapDataTile] = None
    x: Optional[int] = None
    y: Optional[int] = None
    z: Optional[int] = None
    isLinear: Optional[bool] = None
    ignoreWall: Optional[bool] = None
    virtualWall: Optional[bool] = None


@dataclass
class JsonMapData:
    name: str
    length: int
    height: int
    width: int
    leagueType: str
    duration: int
    finished: bool
    startTile: JsonMapDataTilePosition
    cells: Dict[str, JsonMapDataCell]


class Field:
    def __init__(self, name):
        self.name = name
        self.jsonMapData = None
        self.mapData = None
        self.size = (0, 0)  # (length, width)

    # mapDataについて補足
    # mapDataは2次元配列で、各要素は以下のように表される
    # 0: 空白
    # 1: 壁, 柱
    # 2: タイル
    # 壁とタイルをそれぞれ1つのセルとして扱うため、配列のサイズは(2*width+1) x (2*length+1)となる
    # 奇数,奇数はタイル。他は壁。

    def readJson(self, json_data):
        self.jsonMapData = JsonMapData(**json_data)
        self.jsonMapData.cells = {
            key: JsonMapDataCell(**value)
            for key, value in self.jsonMapData.cells.items()
        }
        self.jsonMapData.startTile = JsonMapDataTilePosition(
            **self.jsonMapData.startTile)
        self.name = self.jsonMapData.name
        self.mapData = [[0 for _ in range(2*self.jsonMapData.width+1)] for _ in range(
            2*self.jsonMapData.length+1)]
        self.size = (self.jsonMapData.length, self.jsonMapData.width)
        for key, cell in self.jsonMapData.cells.items():
            print(key, cell)
            y, x, z = map(int, key.split(","))
            if z != 0:
                continue
            if cell.isWall:
                self.mapData[x][y] = 1
                if x % 2 == 0 and y % 2 == 1:  # 縦壁
                    self.mapData[x][y-1] = 1
                    self.mapData[x][y+1] = 1
                elif y % 2 == 0 and x % 2 == 1:  # 横壁
                    self.mapData[x-1][y] = 1
                    self.mapData[x+1][y] = 1
                else:
                    print("Warning: Wall at unexpected position", x, y)

        for i in range(self.size[0]):
            for j in range(self.size[1]):
                self.mapData[2*i+1][2*j+1] = 2
        # StartTileは3
        sx, sy, sz = (self.jsonMapData.startTile.x,
                      self.jsonMapData.startTile.y, self.jsonMapData.startTile.z)
        self.mapData[sy*2+1][sx*2+1] = 3

    def __str__(self):
        mapDataStr = "\n".join(
            ["".join([str(cell) for cell in row]) for row in self.mapData])
        return f"Field(name={self.name}, mapData=\n{mapDataStr})"
    # タイル座標を与えられたときに、そのタイルの周辺の情報を返すメソッド

    def get_tile_info(self, tile_x, tile_y):
        globalX, globalY = tile_x*2+1, tile_y*2+1
        if self.mapData is None:
            raise ValueError("Map data is not loaded.")
        if globalX < 0 or globalX >= self.size[1]*2+1 or globalY < 0 or globalY >= self.size[0]*2+1:
            raise ValueError("Tile coordinates are out of bounds.")

        info = {}
        directions = {
            90: (globalX, globalY - 1),
            270: (globalX, globalY + 1),
            180: (globalX - 1, globalY),
            0: (globalX + 1, globalY)
        }

        for direction, (x, y) in directions.items():
            if 0 <= x < self.size[1]*2+1 and 0 <= y < self.size[0]*2+1:
                cell_value = self.mapData[y][x]
                if cell_value == 0:
                    info[direction] = "empty"
                elif cell_value == 1:
                    info[direction] = "wall"
                elif cell_value == 2:
                    info[direction] = "tile"
                else:
                    info[direction] = "unknown"
            else:
                info[direction] = "out_of_bounds"

        return info


# マップを読み込み
field = Field("TestField")
with open("map.json", "r") as f:
    json_data = json.load(f)
field.readJson(json_data)
print(field.mapData)
print(field)


# マップを表示
# TkinterでGUIを作成
# 空白は薄い灰色。タイルは白。壁は黒。


root = Tk()
root.title("Map Viewer")
root.geometry("800x900")

TitleLabel = Label(root, text="Map Viewer", font=("Helvetica", 16))
TitleLabel.pack(pady=10)


def get_color(cell_value):
    if cell_value == 0:
        return "#D3D3D3"  # Light Gray for empty
    elif cell_value == 1:
        return "#000000"  # Black for wall
    elif cell_value == 2:
        return "#FFFFFF"  # White for tile
    elif cell_value == 3:
        return "#FFFFFF"  # Green for start tile
    else:
        return "#FF0000"  # Red for unknown


canvas = Canvas(root, width=800, height=600, bg="white")
canvas.pack()
small_cell_size = 10
big_cell_size = 50
for i, row in enumerate(field.mapData):
    for j, cell in enumerate(row):
        x0 = (j//2)*(small_cell_size+big_cell_size)+small_cell_size * (j % 2)
        y0 = (i//2)*(small_cell_size+big_cell_size)+small_cell_size * (i % 2)
        x1 = x0 + (big_cell_size if (j % 2 == 1) else small_cell_size)
        y1 = y0 + (big_cell_size if (i % 2 == 1) else small_cell_size)
        color = get_color(cell)
        canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="black")
        if cell == 3:
            canvas.create_text((x0+x1)//2, (y0+y1)//2, text="S",
                               fill="blue", font=("Helvetica", 16, "bold"))


def convertTileToCanvasCoords(tile_x, tile_y):
    canvas_x = (tile_x * 2 + 1) // 2 * \
        (small_cell_size + big_cell_size) + big_cell_size//2+small_cell_size
    canvas_y = (tile_y * 2 + 1) // 2 * \
        (small_cell_size + big_cell_size) + big_cell_size//2+small_cell_size
    return canvas_x, canvas_y


def RunRobot():
    print("Robot is running...")
    canvas.create_text(400, 580, text="Robot is running...",
                       fill="red", font=("Helvetica", 16, "bold"))
    original_x, original_y = convertTileToCanvasCoords(
        field.jsonMapData.startTile.x, field.jsonMapData.startTile.y)
    canvas.delete("robot")
    canvas.create_oval(original_x - 15, original_y - 15, original_x +
                       15, original_y + 15, outline="red", width=2, tag="robot", fill="red")
    canvas.create_oval(original_x - 8, original_y - 14, original_x -
                       4, original_y-4, outline="black", width=2, tag="robot", fill="black")
    canvas.create_oval(original_x + 8, original_y - 14, original_x +
                       4, original_y-4, outline="black", width=2, tag="robot", fill="black")
    canvas.update()
    canvas.after(500)
    pos = (field.jsonMapData.startTile.x, field.jsonMapData.startTile.y)
    robot_dir = 90
    while True:
        # 右手探索
        info = field.get_tile_info(pos[0], pos[1])
        print(info, pos, robot_dir)

        # 右手優先で進む方向を決定
        if info[(robot_dir - 90) % 360] != "wall":  # 右にタイルがある
            robot_dir = (robot_dir + 270) % 360

        elif info[robot_dir] != "wall":  # 前にタイルがある
            pass
        elif info[(robot_dir + 90) % 360] != "wall":  # 左にタイルがある
            robot_dir = (robot_dir + 90) % 360
        else:  # 後ろにタイルがある（行き止まり）
            robot_dir = (robot_dir + 180) % 360

        # ロボットから見て正面方向に1ます進む
        if robot_dir == 90:
            pos = (pos[0], pos[1] - 1)
            canvas.move("robot", 0, -(small_cell_size + big_cell_size))
        elif robot_dir == 270:
            pos = (pos[0], pos[1] + 1)
            canvas.move("robot", 0, small_cell_size + big_cell_size)
        elif robot_dir == 180:
            pos = (pos[0] - 1, pos[1])
            canvas.move("robot", -(small_cell_size + big_cell_size), 0)
        elif robot_dir == 0:
            pos = (pos[0] + 1, pos[1])
            canvas.move("robot", small_cell_size + big_cell_size, 0)
        else:
            print("Error: Invalid robot direction")
            break
        canvas.update()
        canvas.after(200)


runButton = Button(root, text="Run Robot", command=RunRobot)
runButton.pack(pady=10)

root.mainloop()
