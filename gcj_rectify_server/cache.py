import asyncio
import sqlite3
from io import BytesIO
from pathlib import Path

from PIL import Image

from .fetch import fetch_tile
from .utils import (
    get_maps,
    image_to_bytes,
    lonlat_to_xyz,
    wgsbbox_to_gcjbbox,
    xyz_to_bbox,
)


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


async def get_tile_wgs(
    z: int, x: int, y: int, mapid: str, cache_dir: Path
) -> bytes | None:
    """
    获取瓦片(调整为 WGS84 坐标系)
    """
    if z <= 9:
        return None
    wgs_bbox = xyz_to_bbox(x, y, z)
    gcj_bbox = wgsbbox_to_gcjbbox(wgs_bbox)
    left_upper, right_lower = gcj_bbox

    # 计算左上角和右下角的瓦片行列号
    x_min, y_min = lonlat_to_xyz(left_upper[0], left_upper[1], z)  # 左上角
    x_max, y_max = lonlat_to_xyz(right_lower[0], right_lower[1], z)  # 右下角

    # 创建任务列表，异步获取所有需要的瓦片
    gcj_cache = get_gcj_cache(cache_dir)
    tasks = []
    for ax in range(x_min, x_max + 1):
        for ay in range(y_min, y_max + 1):
            tasks.append(gcj_cache.get_tile(mapid, z, ax, ay))

    # 并发执行所有瓦片下载任务
    tiles = await asyncio.gather(*tasks)
    tile_images = [Image.open(BytesIO(content)) for content in tiles]

    # 拼合瓦片
    composite = Image.new(
        "RGBA", ((x_max - x_min + 1) * 256, (y_max - y_min + 1) * 256)
    )

    tile_index = 0
    for i, ax in enumerate(range(x_min, x_max + 1)):
        for j, ay in enumerate(range(y_min, y_max + 1)):
            tile = tile_images[tile_index]
            if tile:
                composite.paste(tile, (i * 256, j * 256))
            tile_index += 1

    # 计算拼合后的瓦片范围
    megred_bbox = xyz_to_bbox(x_min, y_min, z)[0], xyz_to_bbox(x_max, y_max, z)[1]

    x_range = megred_bbox[1][0] - megred_bbox[0][0]
    y_range = megred_bbox[0][1] - megred_bbox[1][1]

    left_percent = (gcj_bbox[0][0] - megred_bbox[0][0]) / x_range
    top_percent = (megred_bbox[0][1] - gcj_bbox[0][1]) / y_range
    img_width, img_height = composite.size
    # 裁剪选区(left, top, right, bottom)
    crop_bbox = (
        int(left_percent * img_width),
        int(top_percent * img_height),
        int(left_percent * img_width) + 256,
        int(top_percent * img_height) + 256,
    )

    # 从拼合的瓦片中裁剪出对应的区域
    croped_image = composite.crop(crop_bbox)
    return image_to_bytes(croped_image)


class TileCache:
    def __init__(self, cache_dir: Path, db_name="cache.db"):
        self.cache_dir = cache_dir
        self.cache_name = db_name
        self.maps = get_maps(cache_dir)
        self.conn = sqlite3.connect(
            cache_dir / self.cache_name,
            check_same_thread=False,
        )
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.init_datebase()

    def normalize_mapid(self, mapid):
        return mapid.replace("-", "_")

    def init_datebase(self):
        print(f"Initializing database {self.cache_name}...")
        cursor = self.conn.cursor()
        for key in self.maps.keys():
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {self.normalize_mapid(key)} ("
                "  z INTEGER NOT NULL,"
                "  x INTEGER NOT NULL,"
                "  y INTEGER NOT NULL,"
                "  data BLOB,"
                "  PRIMARY KEY (z, x, y)"
                ")"
            )
        self.conn.commit()

    def cache_tile(self, mapid, z, x, y, data):
        cursor = self.conn.cursor()
        cursor.execute(
            f"INSERT OR REPLACE INTO {self.normalize_mapid(mapid)} (z, x, y, data) VALUES (?, ?, ?, ?)",
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
            tile = await get_tile_gcj(z, x, y, mapid, self.maps)
            if tile:
                self.cache_tile(mapid, z, x, y, tile)
        return tile


class WGS84TileCache(TileCache):
    def __init__(self, cache_dir: Path):
        super().__init__(cache_dir, db_name="wgs84_cache.db")

    async def get_tile(self, mapid, z, x, y):
        tile = self.get_tile_from_cache(mapid, z, x, y)
        if tile is None:
            tile = await get_tile_wgs(z, x, y, mapid, self.cache_dir)
            if tile:
                self.cache_tile(mapid, z, x, y, tile)
        return tile


# 按缓存目录缓存 SQLite 连接实例，同一个目录复用同一个连接
_gcj_cache_instances: dict[str, TileCache] = {}
_wgs84_cache_instances: dict[str, WGS84TileCache] = {}


def get_gcj_cache(cache_dir: Path) -> TileCache:
    key = str(cache_dir)
    if key not in _gcj_cache_instances:
        _gcj_cache_instances[key] = TileCache(cache_dir)
    return _gcj_cache_instances[key]


def get_wgs84_cache(cache_dir: Path) -> WGS84TileCache:
    key = str(cache_dir)
    if key not in _wgs84_cache_instances:
        _wgs84_cache_instances[key] = WGS84TileCache(cache_dir)
    return _wgs84_cache_instances[key]
