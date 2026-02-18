import json
import random
import sys
import os
from dataclasses import asdict
from typing import List, Tuple, Dict

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.data_models import JsonMapData, JsonMapDataCell, JsonMapDataTile, JsonMapDataTilePosition

def get_key(x: int, y: int, z: int) -> str:
    return f"{x},{y},{z}"

def generate_maze_complex(length=8, width=8, height=1, extra_path_prob=0.3):
    cells: Dict[str, JsonMapDataCell] = {}

    grid_length = length * 2 + 1
    grid_width = width * 2 + 1

    start_x, start_y, start_z = 1, 1, 0
    start_tile_pos = JsonMapDataTilePosition(start_x, start_y, start_z)

    # 1. Initialization
    wall_positions: List[Tuple[int, int, int]] = [] 
    tile_positions: List[Tuple[int, int, int]] = [] 

    for z in range(height):
        for y in range(grid_length):
            for x in range(grid_width):
                key = get_key(x, y, z)

                # Tile (odd, odd)
                if x % 2 == 1 and y % 2 == 1:
                    is_start = (x == start_x and y == start_y and z == start_z)
                    tile_data = JsonMapDataTile(
                        changeFloorTo=z) if is_start else JsonMapDataTile(blue=random.random() < 0.05)
                    cell = JsonMapDataCell(
                        isTile=True, tile=tile_data, x=x, y=y, z=z)
                    tile_positions.append((x, y, z))
                # Outer walls or pillars (even, even)
                elif x == 0 or y == 0 or x == grid_width - 1 or y == grid_length - 1 or (x % 2 == 0 and y % 2 == 0):
                    cell = JsonMapDataCell(
                        isWall=True, halfWall=0, x=x, y=y, z=z)
                # Potential walls (initial state)
                else:
                    cell = JsonMapDataCell(
                        isWall=True, halfWall=0, x=x, y=y, z=z)
                    wall_positions.append((x, y, z)) 

                cells[key] = cell

    # 2. Randomized Prim's Algorithm
    visited_tiles = set([(start_x, start_y, start_z)])
    wall_frontier: List[Tuple[int, int, int]] = []

    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        wx, wy = start_x + dx, start_y + dy
        if 0 < wx < grid_width - 1 and 0 < wy < grid_length - 1:
            wall_frontier.append((wx, wy, start_z))

    while wall_frontier:
        wall_index = random.randrange(len(wall_frontier))
        wx, wy, wz = wall_frontier.pop(wall_index)

        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = wx + dx, wy + dy
            if (nx, ny, wz) in visited_tiles or (nx, ny, wz) in tile_positions:
                neighbors.append((nx, ny, wz))

        if len(neighbors) < 2: continue # Should not happen if logic is correct
        
        tile1 = neighbors[0]
        tile2 = neighbors[1]

        new_tile = None
        if tile1 not in visited_tiles:
            new_tile = tile1
        elif tile2 not in visited_tiles:
            new_tile = tile2

        if new_tile:
            # Open wall
            cells[get_key(wx, wy, wz)].isWall = False
            visited_tiles.add(new_tile)
            nx, ny, nz = new_tile

            # Add new walls to frontier
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nwx, nwy = nx + dx, ny + dy
                wall_pos = (nwx, nwy, nz)

                is_valid_wall = (0 < nwx < grid_width - 1 and
                                 0 < nwy < grid_length - 1 and
                                 not (nwx % 2 == 0 and nwy % 2 == 0))

                if is_valid_wall and wall_pos not in wall_frontier and cells[get_key(nwx, nwy, nz)].isWall:
                    wall_frontier.append(wall_pos)

    # 3. Random Wall Removal (Loops)
    for x, y, z in wall_positions:
        key = get_key(x, y, z)
        if cells[key].isWall:
            if random.random() < extra_path_prob:
                cells[key].isWall = False

    # 4. Create Object
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

if __name__ == "__main__":
    maze = generate_maze_complex(length=8, width=8, height=1, extra_path_prob=0.35)
    with open("generated_maze_complex.json", "w") as f:
        json.dump(asdict(maze), f, indent=4)
    print("Maze generated and saved to generated_maze_complex.json")
