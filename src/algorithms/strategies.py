from typing import Callable, Optional, Set
from ..core.direction import Direction
from ..core.data_models import MappingDataTileInfo
from ..simulation.robot_interface import RobotInterface
from .mapping import Mapping
import time

class ExplorationStrategy:
    def execute_step(self) -> bool:
        """
        Executes one step of exploration (sense -> plan -> act).
        Returns:
             bool: True if exploration is finished.
        """
        raise NotImplementedError

class ReferenceRightHandStrategy(ExplorationStrategy):
    """
    Implements the "Right Hand + Alpha" strategy from the original code (ExploreStep).
    """
    def __init__(self, robot: RobotInterface, on_update_map: Optional[Callable[[], None]] = None):
        self.robot = robot
        self.mapping = Mapping()
        self.not_visited_tiles: Set[tuple[int, int]] = set()
        self.on_update_map = on_update_map
        
    def _update_map(self):
        sensor_data = self.robot.get_sensor_data()
        
        # 1. Update Tile Count
        self.mapping.mappingField.registerTile(
            self.robot.position, 
            incrementVisitTileCount=1
        )
        
        # 2. Update Wall Count (Sense)
        neighbor_walls = {}
        for d in Direction:
            neighbor_walls[d.value] = (sensor_data[d] == "wall")
        
        self.mapping.mappingField.registerWall(self.robot.position, neighbor_walls)

        if self.on_update_map:
            self.on_update_map()

    def _get_neighbor_tile_count(self, direction: Direction) -> int:
        dx, dy = Direction.get_dx_dy(direction)
        neighbor_pos = (self.robot.position[0] + dx, self.robot.position[1] + dy)
        info = self.mapping.mappingField.getTileInfo(neighbor_pos)
        return info.visitTileCount if info else 0

    def execute_step(self) -> bool:
        sensor_data = self.robot.get_sensor_data()
        
        # Explore/Sense
        for direction in Direction: 
            dx, dy = Direction.get_dx_dy(direction)
            neighbor_pos = (self.robot.position[0] + dx, self.robot.position[1] + dy)
            visit_count = self._get_neighbor_tile_count(direction)
            is_wall = sensor_data.get(direction) == "wall"
            
            if visit_count == 0 and not is_wall:
                self.not_visited_tiles.add(neighbor_pos)
                
        self._update_map()
        self.not_visited_tiles.discard(self.robot.position)
        
        if len(self.not_visited_tiles) == 0:
            return True 

        # Decide Direction
        current = self.robot.direction
        
        # Relative directions
        right_dir = Direction((current.value - 90) % 360)
        left_dir = Direction((current.value + 90) % 360)
        front_dir = current
        
        # Counts
        r_cnt = self._get_neighbor_tile_count(right_dir)
        l_cnt = self._get_neighbor_tile_count(left_dir)
        f_cnt = self._get_neighbor_tile_count(front_dir)
        
        # Walls
        r_wall = sensor_data.get(right_dir) == "wall"
        l_wall = sensor_data.get(left_dir) == "wall"
        f_wall = sensor_data.get(front_dir) == "wall"
        
        turn_angle = 0
        
        if not r_wall:
            # Right is open
            if not f_wall and f_cnt < r_cnt:
                # Front is better than Right
                if not l_wall and l_cnt < f_cnt:
                    # Left is best
                    turn_angle = 90
                else:
                    # Front is best
                    turn_angle = 0
            elif not l_wall and l_cnt < r_cnt:
                # Left is better than Right
                turn_angle = 90
            else:
                # Right is best
                turn_angle = -90
        
        elif not f_wall:
             # Right blocked, Front open
             if not l_wall and l_cnt < f_cnt:
                 turn_angle = 90
             else:
                 turn_angle = 0
        
        elif not l_wall:
            # Right blocked, Front blocked, Left open
            turn_angle = 90
        
        else:
            # Dead end
            turn_angle = 180
            
        if turn_angle == 180:
             self.robot.rotate(90)
             self.robot.rotate(90)
        elif turn_angle != 0:
             self.robot.rotate(turn_angle)
            
        self.robot.move_forward()
        return False


class DynamicDijkstraStrategy(ExplorationStrategy):
    def __init__(self, robot: RobotInterface, on_update_map: Optional[Callable[[], None]] = None):
        self.robot = robot
        self.mapping = Mapping()
        self.on_update_map = on_update_map

    def execute_step(self) -> bool:
        # 1. Update Map (Sense)
        # Register neighbors to Mapping
        sensor_data = self.robot.get_sensor_data()
        neighbor_walls = {}
        for d in Direction:
            neighbor_walls[d.value] = (sensor_data[d] == "wall")
        
        # Register Wall
        self.mapping.mappingField.registerWall(self.robot.position, neighbor_walls)
        
        # Register Current Tile (Visited)
        self.mapping.mappingField.registerTile(
            self.robot.position, 
            incrementVisitTileCount=1
        )
        
        # Register Neighbor Tiles (Unvisited if new)
        for d in Direction:
            if sensor_data[d] != "wall":
                dx, dy = Direction.get_dx_dy(d)
                neighbor_pos = (self.robot.position[0] + dx, self.robot.position[1] + dy)
                # Register only if not exists?
                # Mapping.registerTile checks internally.
                # Just register it to ensure it exists in mapData
                self.mapping.mappingField.registerTile(neighbor_pos)

        if self.on_update_map:
            self.on_update_map()

        # 2. Plan (Dijkstra)
        unreached_targets = self.mapping.dijkstra(
            self.robot.position,
            self.robot.direction,
            searchType="nearestUnreached"
        )
        
        if not unreached_targets:
            return True # No unreached tiles found

        # Find nearest
        nearest_pos = min(unreached_targets.keys(), key=lambda p: unreached_targets[p].cost)
        result = unreached_targets[nearest_pos]
        route = result.route
        
        if len(route) < 2:
            # Already there?
            return True
            
        next_pos = route[1]
        
        # 3. Act
        # Calculate direction to next_pos
        dx = next_pos[0] - self.robot.position[0]
        dy = next_pos[1] - self.robot.position[1]
        
        target_dir = None
        if dx == 1 and dy == 0: target_dir = Direction.EAST
        elif dx == -1 and dy == 0: target_dir = Direction.WEST
        elif dx == 0 and dy == 1: target_dir = Direction.SOUTH # y+1 is South
        elif dx == 0 and dy == -1: target_dir = Direction.NORTH # y-1 is North
        
        if target_dir is None:
             print("Error: Invalid next position in route")
             return True
             
        # Turn
        current_val = self.robot.direction.value
        target_val = target_dir.value
        
        diff = (target_val - current_val + 360) % 360
        
        if diff == 90:
            self.robot.rotate(90)
        elif diff == 180:
            self.robot.rotate(90)
            self.robot.rotate(90)
        elif diff == 270:
            self.robot.rotate(-90)
            
        self.robot.move_forward()
        return False
