from tkinter import IntVar
import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class JsonMapDataTilePosition:
    x: int
    y: int
    z: int


@dataclass
class JsonMapDataTile:
    changeFloorTo: Optional[int] = None
    victims: Optional[Dict[str, str]] = None
    blue: Optional[bool] = False
    reachable: Optional[bool] = True
    checkpoint: Optional[bool] = False
    speedbump: Optional[bool] = False
    black: Optional[bool] = False
    ramp: Optional[bool] = False
    steps: Optional[bool] = False
    red: Optional[bool] = False


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
    # 3: 沼
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
                    pass
                    # print("Warning: Wall at unexpected position", x, y)
            if cell.isTile:
                cell.tile = JsonMapDataTile(
                    **cell.tile) if cell.tile is not None else None

                if cell.tile is None:
                    continue
                if cell.tile.reachable is False:
                    continue
                #print("Tile at", x, y, cell.tile)
                #print(len(self.mapData), len(self.mapData[0]))
                self.mapData[x][y] = 2

                if (cell.tile is not None) and cell.tile.blue:
                    self.mapData[x][y] = 4
                    #print("Swamp at", x, y)

        for i in range(self.size[0]):
            for j in range(self.size[1]):
                # self.mapData[2*i+1][2*j+1] = 2
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
                elif cell_value == 4:
                    info[direction] = "swamp"
                else:
                    info[direction] = "unknown"
            else:
                info[direction] = "out_of_bounds"

        return info

