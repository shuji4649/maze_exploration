import math
from typing import Dict, Optional, Tuple
from ..core.data_models import MappingDataTileInfo, MappingDataWallInfo
from ..core.direction import Direction
from .pathfinding import dijkstra, DijkstraResult


class MappingField:
    def __init__(self):
        self.mapData: Dict[
            Tuple[int, int], MappingDataTileInfo | MappingDataWallInfo
        ] = {}
        # Key is fieldCoord. fieldCoord = tileCoord * 2 + startTileOffset
        # Field assumes walls on edges, so first tile is at (1, 1)
        self.startTile = (1, 1)

    def tileCoord2FieldCoord(self, tile_x, tile_y):
        return (tile_x * 2 + self.startTile[0], tile_y * 2 + self.startTile[1])

    def fieldCoord2TileCoord(self, field_x, field_y):
        return ((field_x - self.startTile[0]) // 2, (field_y - self.startTile[1]) // 2)

    def registerTile(
        self,
        tileCoord: Tuple[int, int],
        tileType: int = -1,
        incrementVisitTileCount: int = 0,
        incrementVisitWallCount: Dict[int, int] = None,
        wallStatus: Dict[int, int] = None,
    ):
        if incrementVisitWallCount is None:
            incrementVisitWallCount = {d.value: 0 for d in Direction}
        if wallStatus is None:
            wallStatus = {d.value: -1 for d in Direction}

        tileInfo = MappingDataTileInfo()
        fieldCoord = self.tileCoord2FieldCoord(*tileCoord)

        if fieldCoord in self.mapData:
            tileInfo = self.mapData[fieldCoord]
            if tileType != -1:
                tileInfo.tileType = tileType
            for d in Direction:
                dir_val = d.value
                if wallStatus.get(dir_val, -1) != -1:
                    tileInfo.wallStatus[dir_val] = wallStatus[dir_val]
        else:
            tileInfo.fieldCoord = fieldCoord
            tileInfo.tileCoord = tileCoord
            tileInfo.tileType = tileType if tileType != -1 else 0
            for d in Direction:
                dir_val = d.value
                tileInfo.wallStatus[dir_val] = wallStatus.get(dir_val, -1)

        tileInfo.visitTileCount += incrementVisitTileCount
        for d in Direction:
            dir_val = d.value
            tileInfo.visitWallCount[dir_val] += incrementVisitWallCount.get(dir_val, 0)

        self.mapData[fieldCoord] = tileInfo

    def registerWall(self, tileCoord: Tuple[int, int], isWallDict: Dict[int, bool]):
        fieldCoord = self.tileCoord2FieldCoord(*tileCoord)

        for dir_val, isWall in isWallDict.items():
            direction = Direction(dir_val)
            dx, dy = Direction.get_dx_dy(direction)
            # Wall position relative to tile field coord?
            # Original code:
            # 0 (East): x+1
            # 90 (North): y-1
            # 180 (West): x-1
            # 270 (South): y+1
            # Wait, 0 (East) is x+1.
            # In original code Field `get_tile_info`:
            # 0: (globalX + 1, globalY)
            # mapping registerWall:
            # 0: (fieldCoord[0] + 1, fieldCoord[1])
            # Matches.

            wallFieldCoord = (fieldCoord[0] + dx, fieldCoord[1] + dy)

            wallInfo = MappingDataWallInfo()
            wallInfo.position = wallFieldCoord
            wallInfo.isWall = isWall

            if wallFieldCoord in self.mapData:
                existingWallInfo = self.mapData[wallFieldCoord]
                if isinstance(existingWallInfo, MappingDataWallInfo):
                    if existingWallInfo.isWall != isWall:
                        print(
                            f"Error: Conflicting wall information at {wallFieldCoord}"
                        )
                        return False

            self.mapData[wallFieldCoord] = wallInfo
        return True

    def getWallInfo(
        self, tileCoord: Tuple[int, int]
    ) -> Dict[Direction, Optional[bool]]:
        fieldCoord = self.tileCoord2FieldCoord(*tileCoord)
        wallInfo = {}

        for direction in Direction:
            dx, dy = Direction.get_dx_dy(direction)
            neighbor = (fieldCoord[0] + dx, fieldCoord[1] + dy)

            if neighbor in self.mapData and isinstance(
                self.mapData[neighbor], MappingDataWallInfo
            ):
                wallInfo[direction] = self.mapData[neighbor].isWall
            else:
                wallInfo[direction] = None
        return wallInfo

    def getTileInfo(self, tileCoord: Tuple[int, int]) -> Optional[MappingDataTileInfo]:
        fieldCoord = self.tileCoord2FieldCoord(*tileCoord)
        if fieldCoord in self.mapData and isinstance(
            self.mapData[fieldCoord], MappingDataTileInfo
        ):
            return self.mapData[fieldCoord]
        return None


class Mapping:
    def __init__(self):
        self.mappingField = MappingField()

    def calcNextTileCost(self, current: Tuple[int, int]) -> Dict[Direction, int]:
        costs = {}
        wallInfo = self.mappingField.getWallInfo(current)

        for direction in Direction:
            dx, dy = Direction.get_dx_dy(direction)

            # Check wall
            if wallInfo[direction] is True or wallInfo[direction] is None:
                costs[direction] = math.inf
                continue

            neighbor = (current[0] + dx, current[1] + dy)
            neighborTileInfo = self.mappingField.getTileInfo(neighbor)

            if neighborTileInfo is not None:
                if neighborTileInfo.tileType == 4:  # Swamp
                    costs[direction] = 6
                else:
                    costs[direction] = 1
            else:
                costs[direction] = math.inf
        return costs

    def dijkstra(
        self,
        start: Tuple[int, int],
        startDir: Direction,
        searchType: str = "all",
        turn_90_cost: float = 1,
    ) -> Dict[Tuple[int, int], DijkstraResult]:
        return dijkstra(
            start=start,
            start_dir=startDir,
            calc_costs_func=self.calcNextTileCost,
            is_unreached_func=lambda pos: (
                self.mappingField.getTileInfo(pos) is not None
                and self.mappingField.getTileInfo(pos).visitTileCount == 0
            ),
            search_type=searchType,
            _turn_90_cost=turn_90_cost,
        )

    def calcNextTileCost_include_distance_from_start(
        self, current: Tuple[int, int], k=0
    ) -> Dict[Direction, float]:
        costs = {}
        wallInfo = self.mappingField.getWallInfo(current)

        for direction in Direction:
            dx, dy = Direction.get_dx_dy(direction)

            # Check wall
            if wallInfo[direction] is True or wallInfo[direction] is None:
                costs[direction] = math.inf
                continue

            neighbor = (current[0] + dx, current[1] + dy)
            neighborTileInfo = self.mappingField.getTileInfo(neighbor)

            if neighborTileInfo is not None:
                if neighborTileInfo.tileType == 4:  # Swamp
                    costs[direction] = 6
                else:
                    costs[direction] = 1
            else:
                costs[direction] = math.inf

            # スタート地点までのマンハッタン距離をコストに加算する
            # 修正係数
            # distance_correction_factor = -0.2
            costs[direction] -= k * (
                (
                    abs(neighbor[0] - self.mappingField.startTile[0])
                    + abs(neighbor[1] - self.mappingField.startTile[1])
                )
                - (
                    abs(current[0] - self.mappingField.startTile[0])
                    + abs(current[1] - self.mappingField.startTile[1])
                )
            )
            if costs[direction] < 0:
                costs[direction] = 0

        return costs

    def dijkstra_include_distance_from_start(
        self,
        start: Tuple[int, int],
        startDir: Direction,
        searchType: str = "all",
        k=0.2,
    ) -> Dict[Tuple[int, int], DijkstraResult]:
        return dijkstra(
            start=start,
            start_dir=startDir,
            calc_costs_func=self.calcNextTileCost_include_distance_from_start,
            is_unreached_func=lambda pos: (
                self.mappingField.getTileInfo(pos) is not None
                and self.mappingField.getTileInfo(pos).visitTileCount == 0
            ),
            search_type=searchType,
            k=k,
        )
