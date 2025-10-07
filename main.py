import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from tkinter import *
from tkinter import ttk
from collections import defaultdict
import os
import heapq
import math
from queue import PriorityQueue


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


@dataclass
class MappingDataTileInfo:
    fieldCoord: tuple[int, int] = (0, 0)  # (x,y) フィールド座標(タイルと壁を含む)
    tileCoord: tuple[int, int] = (0, 0)  # (x,y) タイル座標(タイルのみ)
    tileType: int = 0  # 0: normal, 1: black, 2: swamp, 3: stair
    visitTileCount: int = 0  # そのタイルに訪れた回数
    visitWallCount: dict[int, int] = field(
        default_factory=lambda: {0: 0, 90: 0, 180: 0, 270: 0}
    )  # そのタイルを囲む壁を見た回数 絶対方位
    wallStatus: dict[int, int] = field(
        default_factory=lambda: {0: 0, 90: 0, 180: 0, 270: 0}
    )  # そのタイルを囲む壁の状態 0:未発見 1:発見 絶対方位


@dataclass
class MappingDataWallInfo:
    position: tuple[int] = (0, 0)  # (x,y) #フィールド座標(タイルと壁を含む), 辞書のKeyと一致
    isWall: bool = False  # 壁かどうか # True: 壁, False: 壁なし


# マッピング用フィールド記憶データクラス
class MappingField:
    def __init__(self):
        self.name = ""
        self.mapData: dict[tuple[int],
                           MappingDataTileInfo | MappingDataWallInfo] = {}
        self.startTile = (0, 0)
    # タイル座標とフィールド座標の変換

    def tileCoord2FieldCoord(self, tile_x, tile_y):
        return (tile_x * 2 + self.startTile[0], tile_y * 2 + self.startTile[1])
    # フィールド座標とタイル座標の変換

    def fieldCoord2TileCoord(self, field_x, field_y):
        return ((field_x - self.startTile[0]) // 2, (field_y - self.startTile[1]) // 2)
    # タイル情報の登録・更新。タイル座標と、タイルタイプ、訪問回数の増分、壁の訪問回数の増分、壁の状態を示す辞書を与える

    def registerTile(self, tileCoord: tuple[int], tileType: int = -1, incrementVisitTileCount: int = 0, incrementVisitWallCount: dict[int, int] = {0: 0, 90: 0, 180: 0, 270: 0}, wallStatus: dict[int, int] = {0: -1, 90: -1, 180: -1, 270: -1}):
        tileInfo = MappingDataTileInfo()
        fieldCoord = self.tileCoord2FieldCoord(*tileCoord)
        if fieldCoord in self.mapData.keys():
            tileInfo = self.mapData[fieldCoord]
            if tileType != -1:
                tileInfo.tileType = tileType
            for dir in [0, 90, 180, 270]:
                if wallStatus.get(dir, -1) != -1:
                    tileInfo.wallStatus[dir] = wallStatus[dir]
        else:
            tileInfo.fieldCoord = fieldCoord
            tileInfo.tileCoord = tileCoord
            tileInfo.tileType = tileType if tileType != -1 else 0
            for dir in [0, 90, 180, 270]:
                tileInfo.wallStatus[dir] = wallStatus.get(dir, -1)
        tileInfo.visitTileCount += incrementVisitTileCount
        for dir in [0, 90, 180, 270]:
            tileInfo.visitWallCount[dir] += incrementVisitWallCount.get(dir, 0)
        self.mapData[fieldCoord] = tileInfo

    # 壁情報の登録。タイル座標と、そのタイルに隣接する四方向の壁の有無を示す辞書を与える
    def registerWall(self, tileCoord: tuple[int], isWallDict: dict[int, bool]):
        fieldCoord = self.tileCoord2FieldCoord(*tileCoord)
        for dir, isWall in isWallDict.items():
            wallFieldCoord = None
            if dir == 0:
                wallFieldCoord = (fieldCoord[0] + 1, fieldCoord[1])
            elif dir == 90:
                wallFieldCoord = (fieldCoord[0], fieldCoord[1] - 1)
            elif dir == 180:
                wallFieldCoord = (fieldCoord[0] - 1, fieldCoord[1])
            elif dir == 270:
                wallFieldCoord = (fieldCoord[0], fieldCoord[1] + 1)
            if wallFieldCoord is not None:
                wallInfo = MappingDataWallInfo()
                wallInfo.position = wallFieldCoord
                wallInfo.isWall = isWall
                self.mapData[wallFieldCoord] = wallInfo
    # 指定したタイルから隣接四方向の壁の有無を返す

    def getWallInfo(self, tileCoord: tuple[int]) -> dict[int, bool]:
        fieldCoord = self.tileCoord2FieldCoord(*tileCoord)
        wallInfo = {}
        directions = {
            0: (1, 0),
            90: (0, -1),
            180: (-1, 0),
            270: (0, 1)
        }
        for direction, (dx, dy) in directions.items():
            neighbor = (fieldCoord[0] + dx, fieldCoord[1] + dy)
            if neighbor in self.mapData.keys() and isinstance(self.mapData[neighbor], MappingDataWallInfo):
                wallInfo[direction] = self.mapData[neighbor].isWall
            else:
                wallInfo[direction] = None  # 壁情報が未登録
        return wallInfo

    # タイル情報の取得
    def getTileInfo(self, tileCoord: tuple[int]) -> Optional[MappingDataTileInfo]:
        fieldCoord = self.tileCoord2FieldCoord(*tileCoord)
        if fieldCoord in self.mapData.keys() and isinstance(self.mapData[fieldCoord], MappingDataTileInfo):
            return self.mapData[fieldCoord]
        else:
            return None  # タイル情報が未登録


@dataclass
class dijkstraResult:
    cost: int
    route: List[tuple[int]]

# マッピングクラス。 マッピング用フィールド記憶データを持ち、経路探索などを行う


class Mapping:
    def __init__(self):
        self.mappingField: MappingField = MappingField()

    # 与えられたタイルから隣接四方向タイルへのコストを計算して返す
    # 黒タイル、沼、階段などは後日コスト変化の実装を追加する
    def calcNextTileCost(self, current: tuple[int]) -> dict[int, int]:
        # 方向は絶対方位
        directions = {
            0: (1, 0),
            90: (0, -1),
            180: (-1, 0),
            270: (0, 1)
        }
        costs = {}
        # 壁の有無を読み込み
        wallInfo = self.mappingField.getWallInfo(current)
        for direction, (dx, dy) in directions.items():
            if wallInfo[direction] == True or wallInfo[direction] is None:
                costs[direction] = math.inf
                continue
            neighbor = (current[0] + dx, current[1] + dy)
            neighborTileInfo = self.mappingField.getTileInfo(neighbor)
            # 隣接タイルが存在しない or 壁がある場合はコスト無限大
            if neighborTileInfo is not None:
                costs[direction] = 1
            else:
                costs[direction] = math.inf
        return costs

    # ダイクストラ法による最短経路探索
    # start: 探索開始タイルのフィールド座標 (x,y)
    # type: 探索タイプ "all": 全ての未到達タイル, "nearestUnreached": 最も近い未到達タイル、"unreached": 未到達タイル
    def dijkstra(self, start: tuple[int], searchType: str = "all") -> dict[dijkstraResult]:
        q = PriorityQueue()
        q.put((0, start))
        distances = defaultdict(lambda: math.inf)
        distances[start] = 0
        routes: dict[tuple[int], List[tuple[int]]] = {}
        routes[start] = []  # 経路復元用
        unreached: dict[tuple[int], int] = {}  # 未到達タイルのコスト記録用

        while q.qsize() > 0:
            current_distance, current_position = q.get()
            print(q.qsize(), current_distance, current_position)
            if self.mappingField.getTileInfo(current_position).visitTileCount == 0 and current_position != start:
                # 未到達タイルに到達したらコストを記録
                unreached[current_position] = current_distance
                if searchType == "nearestUnreached":
                    break

            # キュー追加後に距離が更新されていた場合はスキップ
            if current_distance > distances[current_position]:
                continue
            # 隣接タイルへのコストを算出
            next_costs = self.calcNextTileCost(current_position)
            for direction, cost in next_costs.items():
                if math.isinf(cost):
                    continue
                neighbor = (current_position[0] + (1 if direction == 0 else -1 if direction == 180 else 0),
                            current_position[1] + (1 if direction == 270 else -1 if direction == 90 else 0))
                distance = current_distance + cost
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    q.put((distance, neighbor))
                    routes[neighbor] = routes[current_position] + \
                        [current_position]

        # 復元経路とコストを合わせてreturn
        returnDict = {}
        for position, cost in distances.items():
            if cost == math.inf:
                continue
            returnDict[position] = dijkstraResult(
                cost=cost, route=routes[position] + [position])

        if searchType == "all":
            return returnDict
        elif searchType == "nearestUnreached" or searchType == "unreached":
            # Unreachedのコストと経路を返す
            returnDict = {k: v for k, v in returnDict.items()
                          if k in unreached.keys()}
            return returnDict
        else:
            raise ValueError("Invalid searchType")

    def __str__(self):
        return f"Mapping(mappingField={self.mappingField})"

    def __repr__(self):
        return self.__str__()

# 探索機クラス。マッピングクラスを持ちながら、ロボットの位置情報等を持ち、実際に探索を指示するクラス。


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

        self.mapping = Mapping()

    def move_forward(self):
        self.updateTileCount()
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
        self.updateWallCount()
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

    def updateTileCount(self):
        self.mapping.mappingField.registerTile(
            self.position, incrementVisitTileCount=1)
        self.drawTileCount(self.position, self.mapping.mappingField.getTileInfo(
            self.position).visitTileCount)

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

    def ExploreStepWithDijkstra(self):
        info = self.field.get_tile_info(
            *self.position)
        directions = {
            0: (1, 0),
            90: (0, -1),
            180: (-1, 0),
            270: (0, 1)
        }
        notVisitedNeighbors = []
        neighborWalls = {}
        for dir, (dx, dy) in directions.items():  # 絶対方位
            if info[dir] == "wall":
                neighborWalls[dir] = True
            else:
                neighborWalls[dir] = False
                # 未到達か確認
                if self.mapping.mappingField.getTileInfo((self.position[0] + dx, self.position[1] + dy)) is None or self.mapping.mappingField.getTileInfo((self.position[0] + dx, self.position[1] + dy)).visitTileCount == 0:
                    notVisitedNeighbors.append(
                        (dir, (self.position[0] + dx, self.position[1] + dy)))
                # 未発見であれば登録
                if self.mapping.mappingField.getTileInfo((self.position[0] + dx, self.position[1] + dy)) is None:
                    self.mapping.mappingField.registerTile(
                        (self.position[0] + dx, self.position[1] + dy))
        # 現在地のタイル情報を登録・更新
        self.mapping.mappingField.registerTile(
            (self.position[0], self.position[1]), incrementVisitTileCount=0)
        # 隣接壁情報を登録・更新
        self.mapping.mappingField.registerWall(
            (self.position[0], self.position[1]), neighborWalls)

        if len(notVisitedNeighbors) > 0:
            # 未到達タイルが隣接している場合はそこに進む
            targetDir, target = notVisitedNeighbors[0]

            turnAngle = (targetDir - self.direction + 360) % 360
            if turnAngle == 90:
                self.rotate(90)
            elif turnAngle == 180:
                self.rotate(90)
                self.rotate(90)
            elif turnAngle == 270:
                self.rotate(-90)
            self.move_forward()
            return False
        else:
            # 未到達タイルが隣接していない場合はダイクストラ法で最も近い未到達タイルを探索
            unreached = self.mapping.dijkstra(
                self.position, "nearestUnreached")
            print("Unreached tiles:", unreached)
            if len(unreached) == 0:
                return True
            nearestTile = min(unreached.items(), key=lambda x: x[1].cost)[0]
            route = unreached[nearestTile].route
            print("Nearest unreached tile:", nearestTile, "Route:", route)
            if len(route) < 2:
                return True
            while len(route) > 1:
                nextPos = route[1]
                dx = nextPos[0] - self.position[0]
                dy = nextPos[1] - self.position[1]
                if dx == 1 and dy == 0:
                    targetDir = 0
                elif dx == -1 and dy == 0:
                    targetDir = 180
                elif dx == 0 and dy == 1:
                    targetDir = 270
                elif dx == 0 and dy == -1:
                    targetDir = 90
                else:
                    print("Error: Invalid next position in route")
                    return True
                turnAngle = (targetDir - self.direction + 360) % 360
                if turnAngle == 90:
                    self.rotate(90)
                elif turnAngle == 180:
                    self.rotate(90)
                    self.rotate(90)
                elif turnAngle == 270:
                    self.rotate(-90)
                self.move_forward()
                route.pop(0)


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
root.geometry("600x800")

TitleLabel = Label(root, text="Map Viewer", font=("Helvetica", 16))
TitleLabel.pack(pady=10)


# ドロップダウンメニューで選択したマップを描画。
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
canvas = Canvas(root, width=800, height=500, bg="white")
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
    canvas.after(100)


def turnFunc(angle):
    global robot_dir
    # 角度に応じてロボットを回転させる（ここでは単純に方向を変えるだけ）
    robot_pos_x, robot_pos_y = canvas.coords(
        "robot")[0]+15, canvas.coords("robot")[1]+15
    if angle == -90:
        robot_dir = (robot_dir + 270) % 360
    elif angle == 90:
        robot_dir = (robot_dir + 90) % 360
    elif angle == 180 or angle == -180:
        robot_dir = (robot_dir + 180) % 360
    else:
        print("Error: Invalid turn angle")

    canvas.delete("robot")
    canvas.create_oval(robot_pos_x - 15, robot_pos_y - 15, robot_pos_x +
                       15, robot_pos_y + 15, outline="red", width=2, tag="robot", fill="red")
    if robot_dir == 90:
        canvas.create_oval(robot_pos_x - 8, robot_pos_y - 14, robot_pos_x -
                           4, robot_pos_y-4, outline="black", width=2, tag="robot", fill="black")
        canvas.create_oval(robot_pos_x + 8, robot_pos_y - 14, robot_pos_x +
                           4, robot_pos_y-4, outline="black", width=2, tag="robot", fill="black")
    elif robot_dir == 270:
        canvas.create_oval(robot_pos_x - 8, robot_pos_y + 14, robot_pos_x -
                           4, robot_pos_y+4, outline="black", width=2, tag="robot", fill="black")
        canvas.create_oval(robot_pos_x + 8, robot_pos_y + 14, robot_pos_x +
                           4, robot_pos_y+4, outline="black", width=2, tag="robot", fill="black")
    elif robot_dir == 180:
        canvas.create_oval(robot_pos_x - 14, robot_pos_y - 8, robot_pos_x -
                           4, robot_pos_y-4, outline="black", width=2, tag="robot", fill="black")
        canvas.create_oval(robot_pos_x - 14, robot_pos_y + 8, robot_pos_x -
                           4, robot_pos_y+4, outline="black", width=2, tag="robot", fill="black")
    elif robot_dir == 0:
        canvas.create_oval(robot_pos_x + 14, robot_pos_y - 8, robot_pos_x +
                           4, robot_pos_y-4, outline="black", width=2, tag="robot", fill="black")
        canvas.create_oval(robot_pos_x + 14, robot_pos_y + 8, robot_pos_x +
                           4, robot_pos_y+4, outline="black", width=2, tag="robot", fill="black")
    else:
        print("Error: Invalid robot direction after turn")
    canvas.update()
    canvas.after(200)


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
