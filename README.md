# gcj-rectify

将 GCJ-02（火星坐标系）地图瓦片实时纠正为 WGS-84 坐标系，提供标准 WMTS 服务。

## 安装

```bash
uv tool install gcj-rectify
```

或直接运行（无需安装）：

```bash
uvx gcj-rectify
```

## 运行服务

开发模式（热重载）：

```bash
uv run uvicorn gcj_rectify_server:app --reload
```

生产模式：

```bash
uv run uvicorn gcj_rectify_server:app --host 0.0.0.0 --port 8000
```

## 缓存

### 缓存目录

默认缓存目录为 `~/.cache/gcj-rectify-cache`，通过环境变量 `GCJRE_CACHE` 可自定义：

```bash
GCJRE_CACHE=/path/to/cache uvx gcj-rectify
```

### 缓存内容

- `cache.db` — GCJ 原始瓦片缓存（SQLite）
- `wgs84_cache.db` — 已纠正到 WGS-84 的瓦片缓存（SQLite）
- `maps.json` — 地图配置，可编辑此文件来增删地图源

## 地图配置

编辑缓存目录下的 `maps.json` 文件来增减地图源，格式如下：

```json
{
  "my-map": {
    "name": "我的地图",
    "url": "https://example.com/tiles/{z}/{x}/{y}.png",
    "min_zoom": 3,
    "max_zoom": 18
  }
}
```
