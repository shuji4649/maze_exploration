from typing import Callable, Optional, Dict, Tuple
from ..core.direction import Direction
from .field import Field

class RobotInterface:
    def __init__(self, field: Field, 
                 move_hook: Optional[Callable[[], None]] = None, 
                 turn_hook: Optional[Callable[[int], None]] = None):
        """
        Args:
            field: The simulation field.
            move_hook: Optional callback when moving forward (e.g. for GUI).
            turn_hook: Optional callback when turning (e.g. for GUI).
        """
        self.field = field
        self.move_hook = move_hook
        self.turn_hook = turn_hook
        
        # Initialize position from field start tile
        start_tile = self.field.jsonMapData.startTile
        self.position = (start_tile.x, start_tile.y)
        self.direction = Direction.NORTH
        self.run_cost = 0

    def move_forward(self) -> bool:
        """
        Moves the robot forward one tile if possible.
        Returns:
            bool: True if move was successful (not blocked), though currently collisions might just happen.
        """
        self.run_cost += 3 # goStraightCost
        
        if self.move_hook:
            self.move_hook()

        dx, dy = Direction.get_dx_dy(self.direction)
        # Note: Direction.get_dx_dy returns standard Cartesian (x+, y+).
        # But our map coordinate system for tiles:
        # NORTH (90) -> y-1
        # SOUTH (270) -> y+1
        # EAST (0) -> x+1
        # WEST (180) -> x-1
        # This matches the Direction.get_dx_dy I implemented?
        # Let's check Direction.get_dx_dy implementation I wrote.
        # NORTH -> (0, -1). Yes.
        
        self.position = (self.position[0] + dx, self.position[1] + dy)
        return True

    def rotate(self, angle: int):
        """
        Rotates the robot.
        Args:
            angle: Angle to rotate (e.g. 90 for left, -90 for right).
        """
        self.run_cost += 1 * (abs(angle) // 90) # turn90Cost
        
        # Update direction
        # Direction is IntEnum.
        # (current + angle) % 360
        new_dir_val = (self.direction.value + angle) % 360
        self.direction = Direction(new_dir_val)

        if self.turn_hook:
            self.turn_hook(angle)

    def get_sensor_data(self) -> Dict[Direction, str]:
        """
        Returns wall/tile info around the current position.
        """
        return self.field.get_tile_info(*self.position)
