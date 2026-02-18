from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

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


@dataclass
class MappingDataTileInfo:
    fieldCoord: tuple[int, int] = (0, 0)  # (x,y)
    tileCoord: tuple[int, int] = (0, 0)  # (x,y)
    tileType: int = 0  # 0: normal, 1: black, 2: swamp, 3: stair, 4: swamp (mapped to 4 in code?) - check logic
    visitTileCount: int = 0
    visitWallCount: dict[int, int] = field(
        default_factory=lambda: {0: 0, 90: 0, 180: 0, 270: 0}
    )
    wallStatus: dict[int, int] = field(
        default_factory=lambda: {0: 0, 90: 0, 180: 0, 270: 0}
    )


@dataclass
class MappingDataWallInfo:
    position: tuple[int] = (0, 0)
    isWall: bool = False
