import argparse
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .cache import get_gcj_cache, get_wgs84_cache
from .fetch import reset_async_client
from .utils import get_cache_dir, get_maps

WMTS_TEMPLATE_PATH = Path(__file__).parent / "wmts.xml"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理

    Args:
        app (FastAPI):
    """
    # 启动时执行
    # 在启动服务器前重置异步客户端，确保使用新的事件循环
    reset_async_client()
    yield
    # 关闭时执行
    from .fetch import close_async_client_async

    await close_async_client_async()


app = FastAPI(lifespan=lifespan)
app.state.cache_dir = get_cache_dir()

# 挂载静态文件目录
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

print(f"Cache Dir: {app.state.cache_dir}")
print(f"Map Config: {app.state.cache_dir.joinpath('maps.json')}")


@app.get("/")
def index():
    return FileResponse(static_dir / "index.html")


@app.get("/config")
def get_config(request: Request):
    return {
        "cache_dir": str(request.app.state.cache_dir),
        "maps": get_maps(request.app.state.cache_dir),
    }


@app.get("/wmts")
async def wmts(request: Request):
    """WMTS GetCapabilities 能力文档"""
    maps = get_maps(request.app.state.cache_dir)
    base_url = str(request.base_url).rstrip("/")

    # 为每个地图生成 Layer 元素
    layers_xml = ""
    for map_id, info in maps.items():
        name = info["name"]
        layer = f"""    <Layer>
      <ows:Title>{name}</ows:Title>
      <ows:Abstract>{name}</ows:Abstract>
      <ows:WGS84BoundingBox>
        <ows:LowerCorner>-180 -85.051129</ows:LowerCorner>
        <ows:UpperCorner>180 85.051129</ows:UpperCorner>
      </ows:WGS84BoundingBox>
      <ows:Identifier>{map_id}</ows:Identifier>
      <Style>
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <TileMatrixSetLink>
        <TileMatrixSet>WebMercatorQuad</TileMatrixSet>
      </TileMatrixSetLink>
      <ResourceURL
                format="image/png"
                resourceType="tile"
                template="{base_url}/tiles/{map_id}/{{TileMatrix}}/{{TileCol}}/{{TileRow}}"
            />
    </Layer>
"""
        layers_xml += layer

    # 读取模板，将 {{layer}} 替换为动态生成的 Layer
    template = WMTS_TEMPLATE_PATH.read_text(encoding="utf-8")
    wmts_xml = template.replace("{{layer}}", layers_xml)

    return Response(content=wmts_xml, media_type="application/xml")


@app.get("/tiles/{map_id}/{z}/{x}/{y}")
async def tile(map_id: str, z: int, x: int, y: int, request: Request):
    """
    Get a tile image for the specified map ID, zoom level, and row/column numbers.

    Args:
        map_id (str): The ID of the map.
        z (int): Zoom level.
        x (int): Tile column number.
        y (int): Tile row number.
    """
    cache_dir: Path = request.app.state.cache_dir
    if z <= 9:
        img_bytes = await get_gcj_cache(cache_dir).get_tile(map_id, z, x, y)
    else:
        img_bytes = await get_wgs84_cache(cache_dir).get_tile(map_id, z, x, y)
    if img_bytes is None:
        # 如果获取瓦片失败，返回空图片或错误响应
        return Response(status_code=500, content="Failed to fetch tile")
    return Response(content=img_bytes, media_type="image/png")


def run(host: str = "0.0.0.0", port: int = 8000):
    """运行 GCJ Rectify 服务器

    Args:
        host: 服务器主机地址，默认为0.0.0.0
        port: 服务器端口，默认为8000
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="GCJ Rectify 服务器")
    parser.add_argument("--host", default=host, help="服务器主机地址 (默认: 0.0.0.0)")
    parser.add_argument(
        "--port", type=int, default=port, help="服务器端口 (默认: 8000)"
    )

    args = parser.parse_args()

    print(f"Server Runing At: http://{args.host}:{args.port}")
    print(f"WMTS Capabilities: http://{args.host}:{args.port}/wmts")
    uvicorn.run(app, host=args.host, port=args.port)
