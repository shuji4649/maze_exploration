import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from tkinter import *
from tkinter import ttk
from collections import defaultdict
import os


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
        # StartTileのx,yを入れ替える
        self.jsonMapData.startTile.x, self.jsonMapData.startTile.y = (
            self.jsonMapData.startTile.x-1)//2, (self.jsonMapData.startTile.y-1)//2
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
                for _x, _y in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    if self.mapData[2*i+1+_x][2*j+1+_y] != 1:
                        break
                else:
                    self.mapData[2*i+1][2*j+1] = 1
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


class Explorer:
    def __init__(self, field: Field, moveForwardFunc: callable, turnFunc: callable, drawWallCount: callable, drawTileCount: callable):
        self.field = field
        self.position = (field.jsonMapData.startTile.x,
                         field.jsonMapData.startTile.y)
        self.direction = 90  # 初期方向は北（上）
        self.moveForwardFunc = moveForwardFunc
        self.turnFunc = turnFunc
        self.WallCount = defaultdict(int)
        self.drawWallCount = drawWallCount
        self.tileCount = defaultdict(int)
        self.drawTileCount = drawTileCount
        self.notVisitedTiles = set()

    def move_forward(self):
        self.moveForwardFunc()
        if self.direction == 90:
            self.position = (self.position[0], self.position[1] - 1)
        elif self.direction == 270:
            self.position = (self.position[0], self.position[1] + 1)
        elif self.direction == 180:
            self.position = (self.position[0] - 1, self.position[1])
        elif self.direction == 0:
            self.position = (self.position[0] + 1, self.position[1])
        else:
            print("Error: Invalid direction")

    def rotate(self, angle):  # 反時計回りが正
        self.direction = (self.direction + angle) % 360
        self.turnFunc(angle)

    def updateWallCount(self):
        info = self.field.get_tile_info(
            *self.position)
        for dir in [(90+self.direction) % 360, (270+self.direction) % 360]:
            if info[dir] == "wall":
                self.WallCount[(self.position[0], self.position[1], dir)] += 1
                self.drawWallCount(
                    self.position[0], self.position[1], dir, self.WallCount[(self.position[0], self.position[1], dir)])

    def dir2NextPos(self, dir):
        direction = (self.direction + dir) % 360
        if direction == 90:
            return (self.position[0], self.position[1]-1)
        elif direction == 270:
            return (self.position[0], self.position[1]+1)
        elif direction == 180:
            return (self.position[0]-1, self.position[1])
        elif direction == 0:
            return (self.position[0]+1, self.position[1])
        else:
            print("Error: Invalid direction")
            return self.position



    # 右手法 + α
    def ExploreStep(self):
        info = self.field.get_tile_info(
            *self.position)

        print(info, self.position, self.direction)
        wallCnt = 0
        for dir in [0, 90, 180, 270]:
            if self.tileCount[self.dir2NextPos(dir)] == 0 and info[(self.direction + dir) % 360] != "wall":
                self.notVisitedTiles.add(self.dir2NextPos(dir))
            if self.tileCount[self.dir2NextPos(dir)] == 1000:
                info[(self.direction + dir) % 360] = "wall"
            if info[(self.direction + dir) % 360] == "wall":
                wallCnt += 1

        self.updateWallCount()
        self.tileCount[self.position] += 1
        self.notVisitedTiles.discard(self.position)
        self.drawTileCount(self.position, self.tileCount[self.position])

        if wallCnt == 3:
            self.tileCount[self.position] = 1000  # 行き止まりは非常に多く通ったことにする
            self.drawTileCount(self.position, self.tileCount[self.position])

        if len(self.notVisitedTiles) == 0:
            return True
        # 右手優先で進む方向を決定
        if info[(self.direction - 90) % 360] != "wall":  # 右にタイルがある
            # 前にタイルがある
            if info[self.direction] != "wall" and self.tileCount[self.dir2NextPos(0)] < self.tileCount[self.dir2NextPos(-90)]:
                self.rotate(0)
            elif info[(self.direction+90) % 360] != "wall" and self.tileCount[self.dir2NextPos(90)] < self.tileCount[self.dir2NextPos(-90)]:  # 後ろにタイルがある
                self.rotate(90)
                self.updateWallCount()
            else:
                self.rotate(-90)
                self.updateWallCount()
            self.move_forward()
        elif info[self.direction] != "wall":  # 前にタイルがある
            if info[(self.direction + 90) % 360] != "wall" and self.tileCount[self.dir2NextPos(90)] < self.tileCount[self.dir2NextPos(0)]:  # 左にタイルがある
                self.rotate(90)
                self.updateWallCount()
            self.move_forward()
        elif info[(self.direction + 90) % 360] != "wall":  # 左にタイルがある
            self.rotate(90)
            self.updateWallCount()
            self.move_forward()
        else:  # 後ろにタイルがある（行き止まり）
            self.rotate(90)
            self.updateWallCount()
            self.rotate(90)
            self.updateWallCount()
            self.move_forward()
        return False


# マップを読み込み
field = Field("TestField")
# with open("map.json", "r") as f:
#     json_data = json.load(f)
# field.readJson(json_data)
# print(field.mapData)
# print(field)


# マップを表示
# TkinterでGUIを作成
# 空白は薄い灰色。タイルは白。壁は黒。


root = Tk()
root.title("Map Viewer")
root.geometry("800x900")

TitleLabel = Label(root, text="Map Viewer", font=("Helvetica", 16))
TitleLabel.pack(pady=10)


# maps/の中のJSONファイルを読み込むドロップダウンメニューを作成
def load_map_from_file(file_path):
    global field, canvas, pos, robot_dir, robot_isRun
    with open(file_path, "r") as f:
        json_data = json.load(f)
    field.readJson(json_data)
    print(field.mapData)
    print(field)
    canvas.delete("all")
    for i, row in enumerate(field.mapData):
        for j, cell in enumerate(row):
            x0 = (j//2)*(small_cell_size+big_cell_size) + \
                small_cell_size * (j % 2)
            y0 = (i//2)*(small_cell_size+big_cell_size) + \
                small_cell_size * (i % 2)
            x1 = x0 + (big_cell_size if (j % 2 == 1) else small_cell_size)
            y1 = y0 + (big_cell_size if (i % 2 == 1) else small_cell_size)
            color = get_color(cell)
            canvas.create_rectangle(
                x0, y0, x1, y1, fill=color, outline="black", tag=f"cell_{i}_{j}")
            if cell == 3:
                canvas.create_text((x0+x1)//2, (y0+y1)//2, text="S",
                                   fill="blue", font=("Helvetica", 16, "bold"))
    pos = (field.jsonMapData.startTile.x, field.jsonMapData.startTile.y)
    robot_dir = 90
    robot_isRun = False


#  mapフォルダにあるものを自動でリストとして取得
map_files = ["maps/" + f for f in os.listdir("maps/") if f.endswith(".json")]

selected_map = StringVar()
selected_map.set(map_files[0])
map_dropdown = OptionMenu(root, selected_map, *
                          map_files, command=load_map_from_file)
map_dropdown.pack(pady=10)
canvas = Canvas(root, width=800, height=600, bg="white")
canvas.pack()


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


small_cell_size = 10
big_cell_size = 50
# for i, row in enumerate(field.mapData):
#     for j, cell in enumerate(row):
#         x0 = (j//2)*(small_cell_size+big_cell_size)+small_cell_size * (j % 2)
#         y0 = (i//2)*(small_cell_size+big_cell_size)+small_cell_size * (i % 2)
#         x1 = x0 + (big_cell_size if (j % 2 == 1) else small_cell_size)
#         y1 = y0 + (big_cell_size if (i % 2 == 1) else small_cell_size)
#         color = get_color(cell)
#         canvas.create_rectangle(
#             x0, y0, x1, y1, fill=color, outline="black", tag=f"cell_{i}_{j}")
#         if cell == 3:
#             canvas.create_text((x0+x1)//2, (y0+y1)//2, text="S",
#                                fill="blue", font=("Helvetica", 16, "bold"))


def convertTileToCanvasCoords(tile_x, tile_y):
    canvas_x = (tile_x * 2 + 1) // 2 * \
        (small_cell_size + big_cell_size) + big_cell_size//2+small_cell_size
    canvas_y = (tile_y * 2 + 1) // 2 * \
        (small_cell_size + big_cell_size) + big_cell_size//2+small_cell_size
    return canvas_x, canvas_y


pos = (0, 0)
robot_dir = 90
robot_isRun = False


def RunRobot():
    global pos, robot_dir, robot_isRun
    # タイルと壁の数をリセット
    for x in range(field.size[1]):
        for y in range(field.size[0]):
            for dir in [0, 90, 180, 270]:
                canvas.delete(f"wallcount_{x}_{y}_{dir}")
            canvas.delete(f"tilecount_{x}_{y}")
    print("Robot is running...")
    canvas.delete("status")
    canvas.create_text(400, 580, text="Robot is running...",
                       fill="red", font=("Helvetica", 16, "bold"), tag="status")
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
    robot_isRun = True
    explorer = Explorer(field, moveForwardFunc, turnFunc,
                        drawWallCount, drawTileCount)
    while robot_isRun:
        if explorer.ExploreStep():
            print("Exploration completed.")
            canvas.delete("status")
            canvas.create_text(400, 580, text="Exploration completed.",
                               fill="red", font=("Helvetica", 16, "bold"), tag="status")
            robot_isRun = False


def moveForwardFunc():
    global pos, robot_dir
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
    canvas.update()
    canvas.after(50)


def turnFunc(angle):
    global robot_dir
    # 角度に応じてロボットを回転させる（ここでは単純に方向を変えるだけ）
    if angle == -90:
        robot_dir = (robot_dir + 270) % 360
    elif angle == 90:
        robot_dir = (robot_dir + 90) % 360
    elif angle == 180 or angle == -180:
        robot_dir = (robot_dir + 180) % 360
    else:
        print("Error: Invalid turn angle")
    canvas.update()
    canvas.after(100)


def drawWallCount(x, y, dir, count):
    if not showWallCountToggle.get():
        return
    canvas_x, canvas_y = convertTileToCanvasCoords(x, y)
    if dir == 0:
        canvas_x += 20
    elif dir == 180:
        canvas_x -= 20
    elif dir == 90:
        canvas_y -= 20
    elif dir == 270:
        canvas_y += 20

    canvas.delete(f"wallcount_{x}_{y}_{dir}")
    canvas.create_text(canvas_x, canvas_y, text=str(count),
                       fill="blue", font=("Helvetica", 12, "bold"), tag=f"wallcount_{x}_{y}_{dir}")


def drawTileCount(position, count):
    if not showTileCountToggle.get():
        return
    x, y = position
    canvas_x, canvas_y = convertTileToCanvasCoords(x, y)
    canvas.delete(f"tilecount_{x}_{y}")
    canvas.create_text(canvas_x, canvas_y, text=str(count),
                       fill="green", font=("Helvetica", 12, "bold"), tag=f"tilecount_{x}_{y}")


def StopRobot():
    global robot_isRun
    robot_isRun = False
    canvas.delete("status")
    canvas.create_text(400, 580, text="Robot stopped.",
                       fill="red", font=("Helvetica", 16, "bold"), tag="status")
    print("Robot stopped.")


runButton = Button(root, text="Run Robot", command=RunRobot)
runButton.pack(pady=10)
stopButton = Button(root, text="Stop Robot", command=StopRobot)
stopButton.pack(pady=10)

showTileCountToggle = BooleanVar()
showTileCountToggle.set(True)
showTileCountToggleCheckbutton = Checkbutton(
    root, text=u"Show Tile Count", variable=showTileCountToggle)
showTileCountToggleCheckbutton.pack(pady=10)

showWallCountToggle = BooleanVar()
showWallCountToggle.set(True)
showWallCountToggleCheckbutton = Checkbutton(
    root, text=u"Show Wall Count", variable=showWallCountToggle)
showWallCountToggleCheckbutton.pack(pady=10)


root.mainloop()
