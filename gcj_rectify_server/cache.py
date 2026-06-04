import sqlite3

from .fetch import fetch_tile
from .utils import gcj_maps, get_cache_dir


async def get_tile_gcj(z: int, x: int, y: int, mapid: str, map_data) -> bytes:
    """
    获取指定行列号的瓦片，这里下载的是原始瓦片(GCJ02 坐标系)。
    Args:
        x (int): Tile X coordinate.
        y (int): Tile Y coordinate.
        z (int): Zoom level.
        mapid (str): Map Id
        map_data: GCJ Maps
    Returns:
        bytes: Tile image bytes.
    """
    url = map_data[mapid]["url"]
    if "-y" in url:
        # 如果 URL 中包含 -y，认为是TMS格式，需要调整 Y 值
        url = url.replace("-y", "y")
        url = url.format(x=x, y=(2**z - 1 - y), z=z)
    else:
        url = url.format(x=x, y=y, z=z)

    # 使用异步HTTP客户端获取瓦片
    content = await fetch_tile(url)

    return content


class TileCache:
    def __init__(self):
        self.conn = sqlite3.connect(get_cache_dir() / self.cache_name())
        self.init_datebase()

    def cache_name(self):
        return "cache.db"

    def normalize_mapid(self, mapid):
        return mapid.replace("-", "_")

    def init_datebase(self):
        cursor = self.conn.cursor()
        keys = gcj_maps.keys()
        for key in keys:
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {self.normalize_mapid(key)} (z INTEGER, x INTEGER, y INTEGER, data BLOB)"
            )
        self.conn.commit()

    def cache_tile(self, mapid, z, x, y, data):
        cursor = self.conn.cursor()
        cursor.execute(
            f"INSERT INTO {self.normalize_mapid(mapid)} ( z, x, y, data) VALUES (?, ?, ?, ?)",
            (z, x, y, data),
        )
        self.conn.commit()

    def get_tile_from_cache(self, mapid, z, x, y):
        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT data FROM {self.normalize_mapid(mapid)} WHERE z = ? AND x = ? AND y = ?",
            (z, x, y),
        )
        result = cursor.fetchone()
        return result[0] if result else None

    async def get_tile(self, mapid, z, x, y):
        tile = self.get_tile_from_cache(mapid, z, x, y)
        if tile is None:
            tile = await get_tile_gcj(z, x, y, mapid, gcj_maps)
            if tile:
                self.cache_tile(mapid, z, x, y, tile)
        return tile
