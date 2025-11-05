import json
import random
from dataclasses import dataclass, asdict
from typing import Dict, Optional


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

# ---------------------------
# 迷路生成関数
# ---------------------------


def generate_maze(length=5, width=5, height=1, wall_prob=0.3):
    cells = {}
    # スタート位置
    start_x, start_y, start_z = 1, 1, 0
    start_tile = JsonMapDataTilePosition(start_x, start_y, start_z)

    for z in range(height):
        for y in range(length*2+1):
            for x in range(width*2+1):
                key = f"{x},{y},{z}"
                # スタートは必ずタイル
                if x == start_x and y == start_y and z == start_z:
                    cell = JsonMapDataCell(isTile=True, tile=JsonMapDataTile(
                        changeFloorTo=z), x=x, y=y, z=z)
                else:
                    if x % 2 == 1 and y % 2 == 1:
                        cell = JsonMapDataCell(
                            isTile=True, tile=JsonMapDataTile(),  x=x, y=y, z=z)
                    elif x % 2 == 0 and y % 2 == 0:
                        continue
                    # ランダムに壁かタイルかを決定
                    elif x == 0 or y == 0 or x == width*2 or y == length*2:
                        cell = JsonMapDataCell(
                            isWall=True, halfWall=0, x=x, y=y, z=z)
                    elif random.random() < wall_prob:
                        cell = JsonMapDataCell(
                            isWall=True, halfWall=0, x=x, y=y, z=z)
                    else:
                        cell = JsonMapDataCell(
                            isWall=False, halfWall=0, x=x, y=y, z=z)
                cells[key] = cell

    maze = JsonMapData(
        name="Generated Maze",
        length=length,
        width=width,
        height=height,
        leagueType="standard",
        duration=480,
        finished=False,
        startTile=start_tile,
        cells=cells
    )

    return maze



# ---------------------------
# JSONに変換して保存
# ---------------------------
maze = generate_maze(length=8, width=8, height=1, wall_prob=0.4)
with open("generated_maze.json", "w") as f:
    json.dump(asdict(maze), f, indent=4)
print("迷路を生成して generated_maze.json に保存しました。")
