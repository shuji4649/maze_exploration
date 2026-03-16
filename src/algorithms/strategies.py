from typing import Callable, List, Optional, Set, Tuple
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

    def __init__(
        self,
        robot: RobotInterface,
        on_update_map: Optional[Callable[[], None]] = None,
        return_to_start: bool = True,
    ):
        self.robot = robot
        self.mapping = Mapping()
        self.not_visited_tiles: Set[tuple[int, int]] = set()
        self.on_update_map = on_update_map
        self.return_to_start = return_to_start
        self._start_position: Tuple[int, int] = robot.position
        self._returning = False
        self._return_route: List[Tuple[int, int]] = []
        self._return_route_index = 0

    def _update_map(self):
        sensor_data = self.robot.get_sensor_data()

        # 1. Update Tile Count
        self.mapping.mappingField.registerTile(
            self.robot.position, incrementVisitTileCount=1
        )

        # 2. Update Wall Count (Sense)
        neighbor_walls = {}
        for d in Direction:
            neighbor_walls[d.value] = sensor_data[d] == "wall"

        self.mapping.mappingField.registerWall(self.robot.position, neighbor_walls)

        if self.on_update_map:
            self.on_update_map()

    def _get_neighbor_tile_count(self, direction: Direction) -> int:
        dx, dy = Direction.get_dx_dy(direction)
        neighbor_pos = (self.robot.position[0] + dx, self.robot.position[1] + dy)
        info = self.mapping.mappingField.getTileInfo(neighbor_pos)
        return info.visitTileCount if info else 0

    def _navigate_to_next(self, next_pos: Tuple[int, int]) -> None:
        """Navigate the robot one step toward next_pos."""
        dx = next_pos[0] - self.robot.position[0]
        dy = next_pos[1] - self.robot.position[1]

        target_dir = None
        if dx == 1 and dy == 0:
            target_dir = Direction.EAST
        elif dx == -1 and dy == 0:
            target_dir = Direction.WEST
        elif dx == 0 and dy == 1:
            target_dir = Direction.SOUTH
        elif dx == 0 and dy == -1:
            target_dir = Direction.NORTH

        if target_dir is None:
            return

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

    def execute_step(self) -> bool:
        # --- Returning phase ---
        if self._returning:
            if self._return_route_index >= len(self._return_route):
                return True  # Arrived at start
            next_pos = self._return_route[self._return_route_index]
            self._navigate_to_next(next_pos)
            self._return_route_index += 1
            if self.on_update_map:
                self.on_update_map()
            return False

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
            if self.return_to_start and self.robot.position != self._start_position:
                # Plan route back to start
                all_results = self.mapping.dijkstra(
                    self.robot.position, self.robot.direction, searchType="all"
                )
                if self._start_position in all_results:
                    route = all_results[self._start_position].route
                    self._return_route = route[1:]  # Skip current position
                    self._return_route_index = 0
                    self._returning = True
                    return False
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
    def __init__(
        self,
        robot: RobotInterface,
        on_update_map: Optional[Callable[[], None]] = None,
        return_to_start: bool = True,
        turn_90_cost: float = 1,
    ):
        self.robot = robot
        self.mapping = Mapping()
        self.on_update_map = on_update_map
        self.return_to_start = return_to_start
        self._start_position: Tuple[int, int] = robot.position
        self._returning = False
        self._return_route: List[Tuple[int, int]] = []
        self._return_route_index = 0
        self.turn_90_cost = turn_90_cost

    def _navigate_to_next(self, next_pos: Tuple[int, int]) -> None:
        """Navigate the robot one step toward next_pos."""
        dx = next_pos[0] - self.robot.position[0]
        dy = next_pos[1] - self.robot.position[1]

        target_dir = None
        if dx == 1 and dy == 0:
            target_dir = Direction.EAST
        elif dx == -1 and dy == 0:
            target_dir = Direction.WEST
        elif dx == 0 and dy == 1:
            target_dir = Direction.SOUTH
        elif dx == 0 and dy == -1:
            target_dir = Direction.NORTH

        if target_dir is None:
            print("Error: Invalid next position in route")
            return

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

    def execute_step(self) -> bool:
        # --- Returning phase ---
        if self._returning:
            if self._return_route_index >= len(self._return_route):
                return True  # Arrived at start
            next_pos = self._return_route[self._return_route_index]
            self._navigate_to_next(next_pos)
            self._return_route_index += 1
            if self.on_update_map:
                self.on_update_map()
            return False

        # 1. Update Map (Sense)
        # Register neighbors to Mapping
        sensor_data = self.robot.get_sensor_data()
        neighbor_walls = {}
        for d in Direction:
            neighbor_walls[d.value] = sensor_data[d] == "wall"

        # Register Wall
        self.mapping.mappingField.registerWall(self.robot.position, neighbor_walls)

        # Register Current Tile (Visited)
        self.mapping.mappingField.registerTile(
            self.robot.position, incrementVisitTileCount=1
        )

        # Register Neighbor Tiles (Unvisited if new)
        for d in Direction:
            if sensor_data[d] != "wall":
                dx, dy = Direction.get_dx_dy(d)
                neighbor_pos = (
                    self.robot.position[0] + dx,
                    self.robot.position[1] + dy,
                )
                self.mapping.mappingField.registerTile(neighbor_pos)

        if self.on_update_map:
            self.on_update_map()

        # 2. Plan (Dijkstra)
        unreached_targets = self.mapping.dijkstra(
            self.robot.position,
            self.robot.direction,
            searchType="nearestUnreached",
            turn_90_cost=self.turn_90_cost,
        )

        if not unreached_targets:
            if self.return_to_start and self.robot.position != self._start_position:
                # Plan route back to start
                all_results = self.mapping.dijkstra(
                    self.robot.position, self.robot.direction, searchType="all"
                )
                if self._start_position in all_results:
                    route = all_results[self._start_position].route
                    self._return_route = route[1:]  # Skip current position
                    self._return_route_index = 0
                    self._returning = True
                    return False
            return True  # No unreached tiles found

        # Find nearest
        nearest_pos = min(
            unreached_targets.keys(), key=lambda p: unreached_targets[p].cost
        )
        result = unreached_targets[nearest_pos]
        route = result.route

        if len(route) < 2:
            # Already there?
            return True

        next_pos = route[1]

        # 3. Act
        self._navigate_to_next(next_pos)
        return False


class DynamicDijkstraIncludeDistanceFromStartStrategy(ExplorationStrategy):
    def __init__(
        self,
        robot: RobotInterface,
        on_update_map: Optional[Callable[[], None]] = None,
        return_to_start: bool = True,
        k=0.2,
    ):
        self.robot = robot
        self.mapping = Mapping()
        self.on_update_map = on_update_map
        self.return_to_start = return_to_start
        self._start_position: Tuple[int, int] = robot.position
        self._returning = False
        self._return_route: List[Tuple[int, int]] = []
        self._return_route_index = 0
        self._k = k

    def _navigate_to_next(self, next_pos: Tuple[int, int]) -> None:
        """Navigate the robot one step toward next_pos."""
        dx = next_pos[0] - self.robot.position[0]
        dy = next_pos[1] - self.robot.position[1]

        target_dir = None
        if dx == 1 and dy == 0:
            target_dir = Direction.EAST
        elif dx == -1 and dy == 0:
            target_dir = Direction.WEST
        elif dx == 0 and dy == 1:
            target_dir = Direction.SOUTH
        elif dx == 0 and dy == -1:
            target_dir = Direction.NORTH

        if target_dir is None:
            print("Error: Invalid next position in route")
            return

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

    def execute_step(self) -> bool:
        # --- Returning phase ---
        if self._returning:
            if self._return_route_index >= len(self._return_route):
                return True  # Arrived at start
            next_pos = self._return_route[self._return_route_index]
            self._navigate_to_next(next_pos)
            self._return_route_index += 1
            if self.on_update_map:
                self.on_update_map()
            return False

        # 1. Update Map (Sense)
        # Register neighbors to Mapping
        sensor_data = self.robot.get_sensor_data()
        neighbor_walls = {}
        for d in Direction:
            neighbor_walls[d.value] = sensor_data[d] == "wall"

        # Register Wall
        self.mapping.mappingField.registerWall(self.robot.position, neighbor_walls)

        # Register Current Tile (Visited)
        self.mapping.mappingField.registerTile(
            self.robot.position, incrementVisitTileCount=1
        )

        # Register Neighbor Tiles (Unvisited if new)
        for d in Direction:
            if sensor_data[d] != "wall":
                dx, dy = Direction.get_dx_dy(d)
                neighbor_pos = (
                    self.robot.position[0] + dx,
                    self.robot.position[1] + dy,
                )
                self.mapping.mappingField.registerTile(neighbor_pos)

        if self.on_update_map:
            self.on_update_map()

        # 2. Plan (Dijkstra)
        unreached_targets = self.mapping.dijkstra_include_distance_from_start(
            self.robot.position,
            self.robot.direction,
            searchType="nearestUnreached",
            k=self._k,
        )

        if not unreached_targets:
            if self.return_to_start and self.robot.position != self._start_position:
                # Plan route back to start
                all_results = self.mapping.dijkstra(
                    self.robot.position, self.robot.direction, searchType="all"
                )
                if self._start_position in all_results:
                    route = all_results[self._start_position].route
                    self._return_route = route[1:]  # Skip current position
                    self._return_route_index = 0
                    self._returning = True
                    return False
            return True  # No unreached tiles found

        # Find nearest
        nearest_pos = min(
            unreached_targets.keys(), key=lambda p: unreached_targets[p].cost
        )
        result = unreached_targets[nearest_pos]
        route = result.route

        if len(route) < 2:
            # Already there?
            return True

        next_pos = route[1]

        # 3. Act
        self._navigate_to_next(next_pos)
        return False


class DynamicDijkstraFarthestFirstStrategy(ExplorationStrategy):
    """
    Dijkstra で全未到達タイルへの最短コストを求め、
    adjusted_cost = cost_from_current - k * manhattan_from_start - k2 * cost_from_start
    が最小のタイルへ向かう戦略。

    - k  : スタートからのマンハッタン距離に掛ける係数
    - k2 : スタートから各タイルへのDijkstraコストに掛ける係数
           k2 > 0 にするとスタートから遠い（経路が長い）タイルを優先する。
    - Dijkstra のコスト計算には手を加えないため負コスト問題が発生しない。
    """

    def __init__(
        self,
        robot: RobotInterface,
        on_update_map: Optional[Callable[[], None]] = None,
        return_to_start: bool = True,
        k: float = 1.0,
        k2: float = 0.0,
    ):
        self.robot = robot
        self.mapping = Mapping()
        self.on_update_map = on_update_map
        self.return_to_start = return_to_start
        self._start_position: Tuple[int, int] = robot.position
        self._start_direction: Direction = robot.direction
        self._returning = False
        self._return_route: List[Tuple[int, int]] = []
        self._return_route_index = 0
        self._k = k
        self._k2 = k2
        # --- Route Cache ---
        self._cached_route: List[Tuple[int, int]] = []
        self._cached_target: Optional[Tuple[int, int]] = None
        self._route_index: int = 0  # 次に向かうべき route インデックス
        self._cached_from_start: dict = {}  # スタートからのDijkstra結果キャッシュ

    def _is_target_unreached(self, pos: Tuple[int, int]) -> bool:
        """目標タイルがまだ未訪問かどうかを返す。"""
        info = self.mapping.mappingField.getTileInfo(pos)
        return info is not None and info.visitTileCount == 0

    def _navigate_to_next(self, next_pos: Tuple[int, int]) -> None:
        """Navigate the robot one step toward next_pos."""
        dx = next_pos[0] - self.robot.position[0]
        dy = next_pos[1] - self.robot.position[1]

        target_dir = None
        if dx == 1 and dy == 0:
            target_dir = Direction.EAST
        elif dx == -1 and dy == 0:
            target_dir = Direction.WEST
        elif dx == 0 and dy == 1:
            target_dir = Direction.SOUTH
        elif dx == 0 and dy == -1:
            target_dir = Direction.NORTH

        if target_dir is None:
            print("Error: Invalid next position in route")
            return

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

    def execute_step(self) -> bool:
        # --- Returning phase ---
        if self._returning:
            if self._return_route_index >= len(self._return_route):
                return True  # Arrived at start
            next_pos = self._return_route[self._return_route_index]
            self._navigate_to_next(next_pos)
            self._return_route_index += 1
            if self.on_update_map:
                self.on_update_map()
            return False

        # 1. Update Map (Sense)
        map_count_before = len(self.mapping.mappingField.mapData)

        sensor_data = self.robot.get_sensor_data()
        neighbor_walls = {}
        for d in Direction:
            neighbor_walls[d.value] = sensor_data[d] == "wall"

        self.mapping.mappingField.registerWall(self.robot.position, neighbor_walls)
        self.mapping.mappingField.registerTile(
            self.robot.position, incrementVisitTileCount=1
        )
        for d in Direction:
            if sensor_data[d] != "wall":
                dx, dy = Direction.get_dx_dy(d)
                neighbor_pos = (
                    self.robot.position[0] + dx,
                    self.robot.position[1] + dy,
                )
                self.mapping.mappingField.registerTile(neighbor_pos)

        if self.on_update_map:
            self.on_update_map()

        map_changed = len(self.mapping.mappingField.mapData) > map_count_before

        # 2. キャッシュの有効性判定
        cache_valid = (
            self._cached_target is not None
            and self._route_index < len(self._cached_route)
            and not map_changed
            and self._is_target_unreached(self._cached_target)
        )

        if not cache_valid:
            # 2-1. 通常のDijkstraで全未到達タイルへの最短コストを取得
            all_unreached = self.mapping.dijkstra(
                self.robot.position, self.robot.direction, searchType="unreached"
            )

            if not all_unreached:
                if self.return_to_start and self.robot.position != self._start_position:
                    all_results = self.mapping.dijkstra(
                        self.robot.position, self.robot.direction, searchType="all"
                    )
                    if self._start_position in all_results:
                        route = all_results[self._start_position].route
                        self._return_route = route[1:]
                        self._return_route_index = 0
                        self._returning = True
                        return False
                return True  # No unreached tiles found

            # 2-2. スタートから全タイルへのDijkstraコストを取得（k2 > 0 かつマップ変化時のみ再計算）
            if self._k2 != 0 and map_changed:
                self._cached_from_start = self.mapping.dijkstra(
                    self._start_position, self._start_direction, searchType="all"
                )
            elif self._k2 == 0:
                self._cached_from_start = {}

            # 2-3. adjusted_cost = cost_from_current - k * manhattan - k2 * cost_from_start
            def adjusted_cost(pos):
                cost_from_current = all_unreached[pos].cost
                manhattan = abs(pos[0] - self._start_position[0]) + abs(
                    pos[1] - self._start_position[1]
                )
                cost_from_start = (
                    self._cached_from_start[pos].cost
                    if pos in self._cached_from_start
                    else 0
                )
                return (
                    cost_from_current - self._k * manhattan - self._k2 * cost_from_start
                )

            # 2-4. adjusted_cost が最小のタイルを選択し、経路をキャッシュ
            target_pos = min(all_unreached.keys(), key=adjusted_cost)
            result = all_unreached[target_pos]

            if len(result.route) < 2:
                return True

            self._cached_route = result.route
            self._cached_target = target_pos
            self._route_index = 1  # route[0] は現在地、route[1] が次ステップ

        next_pos = self._cached_route[self._route_index]
        self._route_index += 1

        # 3. Act
        self._navigate_to_next(next_pos)
        return False
