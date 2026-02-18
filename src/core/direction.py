from enum import IntEnum

class Direction(IntEnum):
    NORTH = 90
    EAST = 0
    SOUTH = 270
    WEST = 180
    
    @classmethod
    def values(cls):
        return [cls.EAST, cls.NORTH, cls.WEST, cls.SOUTH]

    @classmethod
    def get_dx_dy(cls, direction):
        if direction == cls.NORTH:
            return (0, -1)
        elif direction == cls.SOUTH:
            return (0, 1)
        elif direction == cls.EAST:
            return (1, 0)
        elif direction == cls.WEST:
            return (-1, 0)
        raise ValueError(f"Invalid direction: {direction}")
