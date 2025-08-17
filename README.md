# gcj-rectify

Rectify the map from GCJ-02 to WGS-84 coordinate system

## 运行服务

开发模式 
```bash
uv run uvicorn gcj_rectify_server:app --reload
```

生产模式
```bash
uv run uvicorn gcj_rectify_server:app --host 0.0.0.0 --port 8000
```

直接使用 `uvx` 运行

```bash
uvx gcj-rectify
```

## 缓存位置设置

缓存目录默认为`<cwd>/cache`, 通过环境变量 `GCJRE_CACHE` 来设置缓存目录

编辑缓存目录下的`maps.json`来增减地图