import json
import random
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List, Tuple
import collections

# (JsonMapDataTilePosition, JsonMapDataTile, JsonMapDataCell, JsonMapData の定義は省略 - 元のコードと同じです)


@dataclass
class JsonMapDataTilePosition:
    x: int
    y: int
    z: int


@dataclass
class JsonMapDataTile:
    changeFloorTo: Optional[int] = None
    victims: Optional[Dict[str, str]] = None
    blue: Optional[bool] = True
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
# 迷路生成関数 (改良版 - ランダム・プリム法 + ランダム壁除去)
# ---------------------------


def get_key(x: int, y: int, z: int) -> str:
    return f"{x},{y},{z}"


def generate_maze_complex(length=8, width=8, height=1, extra_path_prob=0.3):
    cells = {}

    grid_length = length * 2 + 1
    grid_width = width * 2 + 1

    start_x, start_y, start_z = 1, 1, 0
    start_tile_pos = JsonMapDataTilePosition(start_x, start_y, start_z)

    # 1. 初期化: 全てをタイルマス/壁として配置
    wall_positions: List[Tuple[int, int, int]] = []  # 通路になる可能性のある壁の位置リスト
    tile_positions: List[Tuple[int, int, int]] = []  # タイルマスの位置リスト

    for z in range(height):
        for y in range(grid_length):
            for x in range(grid_width):
                key = get_key(x, y, z)

                # タイルマス (x, yが共に奇数)
                if x % 2 == 1 and y % 2 == 1:
                    is_start = (x == start_x and y == start_y and z == start_z)
                    tile_data = JsonMapDataTile(
                        changeFloorTo=z) if is_start else JsonMapDataTile(blue=random.random() < 0.05)
                    cell = JsonMapDataCell(
                        isTile=True, tile=tile_data, x=x, y=y, z=z)
                    tile_positions.append((x, y, z))
                # 外周の壁、または偶数/偶数の交差点
                elif x == 0 or y == 0 or x == grid_width - 1 or y == grid_length - 1 or (x % 2 == 0 and y % 2 == 0):
                    cell = JsonMapDataCell(
                        isWall=True, halfWall=0, x=x, y=y, z=z)
                # 壁/通路の位置 (初期は壁)
                else:
                    cell = JsonMapDataCell(
                        isWall=True, halfWall=0, x=x, y=y, z=z)
                    wall_positions.append((x, y, z))  # プリム法の候補リストに追加

                cells[key] = cell

    # 2. ランダム・プリム法: 閉区間を作らない最小の通路を生成

    # 訪問済みタイルマス (迷路/通路に組み込まれたタイル)
    visited_tiles = set([(start_x, start_y, start_z)])
    # 迷路のフロンティアにある壁 (通路に組み込まれたタイルに隣接する壁/通路の位置)
    wall_frontier: List[Tuple[int, int, int]] = []

    # スタートタイルに隣接する壁をフロンティアに追加
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        wx, wy = start_x + dx, start_y + dy
        if 0 < wx < grid_width - 1 and 0 < wy < grid_length - 1:
            wall_frontier.append((wx, wy, start_z))

    # 壁の候補リストからランダムに壁を選び、通路に変える
    while wall_frontier:
        # ランダムに壁を選択 (プリム法の「ランダム」要素)
        wall_index = random.randrange(len(wall_frontier))
        wx, wy, wz = wall_frontier.pop(wall_index)

        # この壁が隔てている2つのタイルマスを特定
        # 1つは既に visited_tiles に含まれているはず
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = wx + dx, wy + dy
            if (nx, ny, wz) in visited_tiles or (nx, ny, wz) in tile_positions:
                neighbors.append((nx, ny, wz))

        # 2つの隣接タイルマスを取得
        tile1 = neighbors[0]
        tile2 = neighbors[1]

        # どちらのタイルがまだ迷路に組み込まれていないかを確認
        new_tile = None
        if tile1 not in visited_tiles:
            new_tile = tile1
        elif tile2 not in visited_tiles:
            new_tile = tile2

        if new_tile:
            # 1. 壁を通路にする
            cells[get_key(wx, wy, wz)].isWall = False

            # 2. 新しいタイルマスを迷路に組み込む
            visited_tiles.add(new_tile)
            nx, ny, nz = new_tile

            # 3. 新しいタイルマスに隣接する未だフロンティアにない壁をフロンティアに追加
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nwx, nwy = nx + dx, ny + dy
                wall_pos = (nwx, nwy, nz)

                # グリッド内、かつ外周・交差点ではない、かつ既にフロンティアにない壁
                is_valid_wall = (0 < nwx < grid_width - 1 and
                                 0 < nwy < grid_length - 1 and
                                 not (nwx % 2 == 0 and nwy % 2 == 0))

                if is_valid_wall and wall_pos not in wall_frontier and cells[get_key(nwx, nwy, nz)].isWall:
                    wall_frontier.append(wall_pos)

    # 3. ランダムな壁の除去 (閉路と広い通路の導入)
    # ステップ2で壁として残った位置のみを対象
    for x, y, z in wall_positions:
        key = get_key(x, y, z)
        # 既に通路になっていない（プリム法で壊されなかった）壁を対象
        if cells[key].isWall:
            if random.random() < extra_path_prob:
                cells[key].isWall = False

    # 4. JsonMapDataオブジェクトを作成
    maze = JsonMapData(
        name="Generated Maze (Prim + Looping)",
        length=length,
        width=width,
        height=height,
        leagueType="standard",
        duration=480,
        finished=False,
        startTile=start_tile_pos,
        cells=cells
    )

    return maze


# ---------------------------
# JSONに変換して保存
# ---------------------------
# extra_path_prob: 0.0 (木構造) 〜 1.0 (ほぼ壁なし) の間で設定
# 0.2〜0.5 程度が、閉路もあって難しい迷路になりやすい
maze = generate_maze_complex(length=8, width=8, height=1, extra_path_prob=0.35)
with open("generated_maze_complex.json", "w") as f:
    json.dump(asdict(maze), f, indent=4)
print("迷路を生成して generated_maze_complex.json に保存しました。")
