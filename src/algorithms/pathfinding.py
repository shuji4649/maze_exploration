import math
from queue import PriorityQueue
from typing import List, Dict, Tuple, Callable
from dataclasses import dataclass
from collections import defaultdict
from ..core.direction import Direction


@dataclass
class DijkstraResult:
    cost: float
    route: List[Tuple[int, int]]


def dijkstra(
    start: Tuple[int, int],
    start_dir: Direction,
    calc_costs_func: Callable[[Tuple[int, int]], Dict[Direction, int]],
    is_unreached_func: Callable[[Tuple[int, int]], bool],
    search_type: str = "all",
    k: float = 0,
    _go_straight_cost: float = 3,
    _turn_90_cost: float = 1,
) -> Dict[Tuple[int, int], DijkstraResult]:
    """
    Dijkstra's algorithm for grid pathfinding.

    Args:
        start: Start position (x, y)
        start_dir: Start direction
        calc_costs_func: Function that returns cost to neighbors. (pos) -> {dir: cost}
        is_unreached_func: Function that returns True if a tile is unreached.
        search_type: "all", "nearestUnreached", "unreached"
    """
    go_straight_cost = _go_straight_cost
    turn_90_cost = _turn_90_cost

    q = PriorityQueue()
    q.put((0, start, start_dir))  # (cost, position, direction)

    # distance map: (position, direction) -> cost
    distances: Dict[Tuple[Tuple[int, int], Direction], float] = defaultdict(
        lambda: math.inf
    )
    distances[(start, start_dir)] = 0

    # routes reconstruction: (position, direction) -> list of positions
    routes: Dict[Tuple[Tuple[int, int], Direction], List[Tuple[int, int]]] = {}
    routes[(start, start_dir)] = []

    unreached: Dict[Tuple[int, int], int] = {}  # pos -> cost

    while not q.empty():
        current_distance, current_position, current_direction = q.get()

        # Check if unreached
        if is_unreached_func(current_position) and current_position != start:
            unreached[current_position] = current_distance
            if search_type == "nearestUnreached":
                break

        if current_distance > distances[(current_position, current_direction)]:
            continue

        next_costs = (
            calc_costs_func(current_position)
            if k == 0
            else calc_costs_func(current_position, k)
        )

        for direction, cost in next_costs.items():
            if math.isinf(cost):
                continue

            # Determine neighbor position
            dx, dy = Direction.get_dx_dy(direction)
            neighbor = (current_position[0] + dx, current_position[1] + dy)

            # Calculate turn cost
            # current_direction and direction are IntEnums.
            # diff = abs(direction - current_direction)
            # if 180 diff -> 2 turns. if 90 or 270 diff -> 1 turn. 0 -> 0 turn.

            diff = abs(int(direction) - int(current_direction))
            if diff == 180:
                turn_cost = turn_90_cost * 2
            elif diff == 90 or diff == 270:
                turn_cost = turn_90_cost
            else:
                turn_cost = 0

            distance = current_distance + cost + go_straight_cost + turn_cost

            if distance < distances[(neighbor, direction)]:
                distances[(neighbor, direction)] = distance
                q.put((distance, neighbor, direction))
                routes[(neighbor, direction)] = routes[
                    (current_position, current_direction)
                ] + [current_position]

    # Reconstruct results
    return_dict = {}

    # Process all visited nodes to find best cost to reach them (ignoring final direction)
    # But wait, original code:
    # for (position, direction), cost in distances.items():
    #     returnDict[position] = min(..., key=lambda x: x.cost)

    for (position, direction), cost in distances.items():
        if cost == math.inf:
            continue

        current_result = DijkstraResult(
            cost=cost, route=routes[(position, direction)] + [position]
        )

        if position not in return_dict or cost < return_dict[position].cost:
            return_dict[position] = current_result

    if search_type == "all":
        return return_dict
    elif search_type == "nearestUnreached" or search_type == "unreached":
        # Filter only unreached
        return {k: v for k, v in return_dict.items() if k in unreached}
    else:
        raise ValueError(f"Invalid searchType: {search_type}")
