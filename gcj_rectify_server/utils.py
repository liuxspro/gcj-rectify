import json
import os
from io import BytesIO
from math import atan, cos, log, pi, sinh, tan
from pathlib import Path

from PIL import Image

# 使用了来自 Geohey-Team 的 qgis-geohey-toolbox 插件中的转换算法
# https://github.com/GeoHey-Team/qgis-geohey-toolbox
from .transform import wgs2gcj

gcj_maps = {
    "amap-vec": {
        "name": "高德地图 - 矢量地图",
        "url": "https://wprd02.is.autonavi.com//appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}",
        "min_zoom": 3,
        "max_zoom": 18,
    },
    "amap-labels": {
        "name": "高德地图 - 矢量注记",
        "url": "http://wprd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
        "min_zoom": 3,
        "max_zoom": 18,
    },
    "amap-sat": {
        "name": "高德地图 - 卫星影像",
        "url": "https://wprd02.is.autonavi.com//appmaptile?lang=zh_cn&size=1&scale=1&style=6&x={x}&y={y}&z={z}",
        "min_zoom": 3,
        "max_zoom": 18,
    },
    "tencent-vec": {
        "name": "腾讯地图 - 矢量地图",
        "url": "http://rt0.map.gtimg.com/realtimerender?z={z}&x={x}&y={-y}&type=vector&style=0",
        "min_zoom": 3,
        "max_zoom": 18,
    },
    "google-street": {
        "name": "Google - Road",
        "url": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&hl=zh-CN",
        "min_zoom": 0,
        "max_zoom": 20,
    },
    "google-lables": {
        "name": "Google - Labels",
        "url": "https://mt1.google.com/vt/lyrs=h&x={x}&y={y}&z={z}&hl=zh-CN",
        "min_zoom": 2,
        "max_zoom": 20,
    },
}


def get_cache_dir() -> Path:
    """
    Get the cache directory from the environment variable or default to the app directory.

    Returns:
        str: The path to the cache directory.
    """
    env_cache = os.getenv("GCJRE_CACHE")
    if env_cache:
        # print(f"Using cache directory from environment: {env_cache}")
        env_cache_dir = Path(env_cache)
        env_cache_dir.mkdir(exist_ok=True)
        return env_cache_dir
    current_cache_dir = Path.cwd().joinpath("cache")
    current_cache_dir.mkdir(exist_ok=True)
    # print(f"Using current directory for cache: {current_cache_dir}")
    return current_cache_dir


def init_map_config(config_path: Path):
    map_file_path = config_path.joinpath("maps.json")
    if not map_file_path.exists():
        with open(str(map_file_path), "w", encoding="utf-8") as f:
            json.dump(gcj_maps, f, indent=2, ensure_ascii=False)


def get_maps(config_path: Path):
    map_file_path = config_path.joinpath("maps.json")
    if not map_file_path.exists():
        init_map_config(config_path)
    with open(map_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def bytes_to_image(content: bytes) -> Image:
    """
    Convert bytes to a PIL Image.

    Args:
        content (bytes): Image data in bytes.

    Returns:
        Image: PIL Image object.
    """
    return Image.open(BytesIO(content))


def image_to_bytes(image: Image, img_format: str = "PNG") -> bytes:
    """
    Convert a PIL Image to bytes.

    Args:
        image (Image): PIL Image object.
        img_format (str): Format to save the image, default is "PNG".

    Returns:
        bytes: Image data in bytes.
    """
    img_buffer = BytesIO()
    image.save(img_buffer, format=img_format)
    img_bytes = img_buffer.getvalue()
    img_buffer.close()
    return img_bytes


def xyz_to_lonlat(x: int, y: int, z: int) -> tuple:
    """
    将XYZ瓦片坐标转换为经纬度（左上角点）。

    Args:
        x (int): Tile X coordinate.
        y (int): Tile Y coordinate.
        z (int): Zoom level.

    Returns:
        tuple: Longitude and latitude in degrees.
    """
    n = 2.0**z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = atan(sinh(pi * (1 - 2 * y / n)))
    lat_deg = lat_rad * 180.0 / pi
    return lon_deg, lat_deg


def lonlat_to_xyz(lon: float, lat: float, z: int) -> tuple:
    """
    Convert longitude and latitude to XYZ tile coordinates.

    Args:
        lon (float): Longitude in degrees.
        lat (float): Latitude in degrees.
        z (int): Zoom level.

    Returns:
        tuple: Tile X and Y coordinates.
    """
    n = 2.0**z
    x = (lon + 180.0) / 360.0 * n
    lat_rad = lat * pi / 180.0
    t = log(tan(lat_rad) + 1 / cos(lat_rad))
    y = (1 - t / pi) * n / 2
    return int(x), int(y)


def xyz_to_bbox(x, y, z):
    """
    Convert XYZ tile coordinates to bounding box coordinates.

    Args:
        x (int): Tile X coordinate.
        y (int): Tile Y coordinate.
        z (int): Zoom level.

    Returns:
        tuple: Bounding box in the format (min_lon, min_lat, max_lon, max_lat).
    """
    left_upper_lon, left_upper_lat = xyz_to_lonlat(x, y, z)
    right_lower_lon, right_lower_lat = xyz_to_lonlat(x + 1, y + 1, z)

    return (left_upper_lon, left_upper_lat), (right_lower_lon, right_lower_lat)


def wgsbbox_to_gcjbbox(wgs_bbox):
    """
    Convert WGS84 bounding box to GCJ02 bounding box.

    Args:
        wgs_bbox (tuple): Bounding box in the format (min_lon, min_lat, max_lon, max_lat).

    Returns:
        tuple: GCJ02 bounding box in the same format.
    """
    left_upper, right_lower = wgs_bbox
    gcj_left_upper = wgs2gcj(left_upper[0], left_upper[1])
    gcj_right_lower = wgs2gcj(right_lower[0], right_lower[1])
    return gcj_left_upper, gcj_right_lower
