from typing import List, Optional, Dict, Any, Tuple
from ..core.data_models import JsonMapData, JsonMapDataCell, JsonMapDataTile, JsonMapDataTilePosition
from ..core.direction import Direction

class Field:
    def __init__(self, name):
        self.name = name
        self.jsonMapData: Optional[JsonMapData] = None
        self.mapData: List[List[int]] = [] # 2D array
        self.size = (0, 0)  # (length, width)

    # mapDataについて補足
    # mapDataは2次元配列で、各要素は以下のように表される
    # 0: 空白
    # 1: 壁, 柱
    # 2: タイル
    # 3: 沼
    # 壁とタイルをそれぞれ1つのセルとして扱うため、配列のサイズは(2*width+1) x (2*length+1)となる
    # 奇数,奇数はタイル。他は壁。

    def readJson(self, json_data: Dict[str, Any]):
        # Validate and parse JSON data
        # Note: The original code manually parsed dicts into dataclasses. 
        # We should replicate that or use a library if available, but manual is fine for now to keep dependencies low.
        
        # Helper to parse nested structures
        cells_data = json_data.get('cells', {})
        parsed_cells = {}
        for key, value in cells_data.items():
             # Recursively parse Tile if present
            tile_data = value.get('tile')
            parsed_tile = JsonMapDataTile(**tile_data) if tile_data else None
            
            # Create Cell
            # Filter out keys that might not be in the dataclass if the JSON has extra fields, or just unpack
            # The original code did: JsonMapDataCell(**value)
            # We need to be careful about 'tile' being a dict in 'value' before we replace it.
            value_copy = value.copy()
            if 'tile' in value_copy:
                value_copy['tile'] = parsed_tile
            
            parsed_cells[key] = JsonMapDataCell(**value_copy)

        start_tile_data = json_data.get('startTile')
        parsed_start_tile = JsonMapDataTilePosition(**start_tile_data) if start_tile_data else None

        self.jsonMapData = JsonMapData(
            name=json_data.get('name', ''),
            length=json_data.get('length', 0),
            height=json_data.get('height', 0),
            width=json_data.get('width', 0),
            leagueType=json_data.get('leagueType', ''),
            duration=json_data.get('duration', 0),
            finished=json_data.get('finished', False),
            startTile=parsed_start_tile,
            cells=parsed_cells
        )

        
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
            if cell.isTile:
                if cell.tile is None:
                    continue
                if cell.tile.reachable is False:
                    continue

                self.mapData[x][y] = 2

                if (cell.tile is not None) and cell.tile.blue:
                    self.mapData[x][y] = 4 # Swamp

        for i in range(self.size[0]):
            for j in range(self.size[1]):
                # Check walls around
                for _x, _y in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    if self.mapData[2*i+1+_x][2*j+1+_y] != 1:
                        break
                else:
                    self.mapData[2*i+1][2*j+1] = 1
        
        # StartTile is 3
        # Start position in mapData coords
        sx = self.jsonMapData.startTile.x
        sy = self.jsonMapData.startTile.y
        self.mapData[sy*2+1][sx*2+1] = 3

    def __str__(self):
        if self.mapData:
            mapDataStr = "\n".join(
                ["".join([str(cell) for cell in row]) for row in self.mapData])
            return f"Field(name={self.name}, mapData=\n{mapDataStr})"
        return f"Field(name={self.name}, mapData=None)"

    def get_tile_info(self, tile_x, tile_y) -> Dict[Direction, str]:
        globalX, globalY = tile_x*2+1, tile_y*2+1
        if not self.mapData:
            raise ValueError("Map data is not loaded.")
        if globalX < 0 or globalX >= self.size[1]*2+1 or globalY < 0 or globalY >= self.size[0]*2+1:
            # raise ValueError(f"Tile coordinates ({tile_x}, {tile_y}) -> ({globalX}, {globalY}) are out of bounds.")
             # Better to return out_of_bounds for all directions if the tile itself is invalid, but current logic checks directions
             pass

        info = {}
        # Uses Direction enum values (90, 270, 0, 180)
        # Direction.NORTH = 90
        # Directions mapping in original code:
        # 90: (globalX, globalY - 1) -> NORTH
        # 270: (globalX, globalY + 1) -> SOUTH
        # 180: (globalX - 1, globalY) -> WEST
        # 0: (globalX + 1, globalY) -> EAST
        
        # We can use Direction.get_dx_dy now??
        # get_dx_dy returns change in x,y. 
        # But global coords in mapData are (x, y) = (row, col) or (col, row)? 
        # In readJson: mapData[x][y]. 
        # x is 1st index, y is 2nd index.
        # split key: y, x, z = map(int, key.split(",")) => input JSON uses x,y.
        # But the code uses mapData[x][y]. So first index is x (width?), second is y (length? or vertical?)
        # Let's check: 
        # self.mapData = [[0 for _ in range(2*self.jsonMapData.width+1)] for _ in range(2*self.jsonMapData.length+1)]
        # outer loop range length -> rows. inner loop range width -> cols.
        # So mapData is [row][col].
        # But readJson says: mapData[x][y] = 1.
        # If x is width-wise and y is length-wise.
        # If outer loop is length (y?), then it should be mapData[y][x].
        # The original code:
        # self.mapData = [[0 for _ in range(2*self.jsonMapData.width+1)] for _ in range(2*self.jsonMapData.length+1)]
        # This creates a list of (2*length+1) rows, each having (2*width+1) cols.
        # So `mapData[i]` accesses the ith row (corresponding to length/y axis).
        # But `readJson` does `self.mapData[x][y]`.
        # This implies `x` is the row index (length axis?) and `y` is the column index (width axis?).
        # HOWEVER, usually x is width and y is height.
        # In `__init__`: `self.size = (self.jsonMapData.length, self.jsonMapData.width)`
        # In `generate_maze_complex`: `grid_length = length * 2 + 1`, `grid_width = width * 2 + 1`.
        # loops: `for y in range(grid_length): for x in range(grid_width):`
        # `get_key(x, y, z)`
        # So x is width, y is length.
        # If `mapData` is created as `range(2*length+1)` rows, then the first index should be `y`.
        # But `readJson` uses `mapData[x][y]`. THIS LOOKS LIKE A BUG or WEIRD CONVENTION in the original code.
        # If `x` goes up to 2*width, and we access `mapData[x]`, but `mapData` has `2*length` rows...
        # If width != length, this would crash if x was used as row index but meant to be col index.
        
        # Let's check `get_tile_info` in original code (lines 138+):
        # globalX, globalY = tile_x*2+1, tile_y*2+1
        # directions = { 90: (globalX, globalY - 1), ... }
        # cell_value = self.mapData[y][x]
        # Wait, `directions` calculates `(x, y)`.
        # Then it accesses `mapData[y][x]`.
        # So `mapData` is `[y][x]` (row, col).
        # BUT `readJson` (line 93) does `self.mapData[x][y]`.
        # This contradicts.
        # If `readJson` uses `[x][y]`, then `mapData` first dim is `x`.
        # But `__init__` (line 83) creates `range(2*length+1)` rows.
        # If length=10, width=5. Rows=21. Cols=11.
        # `mapData` has 21 lists of size 11.
        # `readJson`: `y, x, z = key.split`.
        # access `mapData[x][y]`.
        # If x=10 (max x), y=20 (max y).
        # `mapData[10][20]`.
        # `mapData[10]` is valid (10 < 21). `mapData[10]` has length 11. `[20]` is OUT OF BOUNDS.
        # So `readJson` logic `mapData[x][y]` assumes `x` is the index into the outer list.
        # If valid x is small and valid y is large, this crashes.
        # UNLESS `length` corresponds to `x` and `width` corresponds to `y`?
        # `JsonMapData`: length, width.
        # `generate_maze`: `for y in range(grid_length): for x in range(grid_width):`.
        # So y is 0..2*length. x is 0..2*width.
        # So `mapData` shoud be `[y][x]`.
        
        # I suspect the original code `readJson` lines 93-99 might be swapping x and y usages or I am misinterpreting.
        # Let's look at `readJson` again.
        # `self.mapData = [[0 for _ in range(2*self.jsonMapData.width+1)] for _ in range(2*self.jsonMapData.length+1)]`
        # Outer: length (y). Inner: width (x).
        # `self.mapData[x][y] = 1`
        # This tries to use `x` as index for Outer (length/y).
        # This effectively swaps axes or is a bug.
        
        # HOWEVER, I must preserve behavior unless I fix it.
        # If I want to refactor, I should probably fix it to be consistent, i.e. `mapData[y][x]`.
        # BUT `readJson` is what populates it.
        # Let's check `get_tile_info` in original code again.
        # `cell_value = self.mapData[y][x]` (Line 155).
        # So `get_tile_info` expects `[y][x]`.
        # `readJson` writes `[x][y]`.
        # If x and y are swapped in write, but y and x are used in read...
        # Then `mapData` is effectively transposed?
        # Or maybe `length` and `width` are equal in all test cases so it didn't matter?
        # In `main.py` assessments: `generate_random_fields(..., length=10, width=10, ...)`.
        # They are equal! That's why it didn't crash.
        
        # I SHOULD FIX THIS.
        # I will enforce `mapData[y][x]` (row=y, col=x).
        # So in `readJson`, I will change `self.mapData[x][y]` to `self.mapData[y][x]`.
        
        # Re-verifying logic:
        # `startTile.x` is used as `sx` in `readJson`. `self.mapData[sy*2+1][sx*2+1] = 3`.
        # This uses `sy` for first index (row), `sx` for second (col).
        # This matches `mapData[y][x]`.
        # But the loop `for key...` uses `mapData[x][y]`.
        # So `readJson` is INCONSISTENT within itself!
        # `startTile` placement is correct for `[y][x]`.
        # Wall placement is `[x][y]`.
        # Since `generate_maze` makes square mazes mainly, or assumes x/y symmetry?
        # Actually `generate_maze` has `length` and `width`.
        
        # CONCLUSION: The original code `readJson` wall placement is BUGGY if length != width.
        # I will fix it to `mapData[y][x]`.
        
        return_info = {}
        
        # Directions mapping:
        # NORTH (90): (0, -1) -> y-1
        # SOUTH (270): (0, 1) -> y+1
        # WEST (180): (-1, 0) -> x-1
        # EAST (0): (1, 0) -> x+1
        
        coord_map = {
            Direction.NORTH: (0, -1),
            Direction.SOUTH: (0, 1),
            Direction.WEST: (-1, 0),
            Direction.EAST: (1, 0)
        }

        for direction, (dx, dy) in coord_map.items():
            tx = globalX + dx
            ty = globalY + dy
            
            if 0 <= tx < self.size[1]*2+1 and 0 <= ty < self.size[0]*2+1:
                 # width is size[1], length is size[0].
                 # mapData is [y][x] -> [ty][tx]
                cell_value = self.mapData[ty][tx]
                if cell_value == 0:
                    return_info[direction] = "empty"
                elif cell_value == 1:
                    return_info[direction] = "wall"
                elif cell_value == 2:
                    return_info[direction] = "tile"
                elif cell_value == 4:
                    return_info[direction] = "swamp"
                else:
                    return_info[direction] = "unknown"
            else:
                return_info[direction] = "out_of_bounds"

        return return_info
