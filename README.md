# gcj-rectify

## 运行服务

```bash
# 开发模式
uv run uvicorn gcj_rectify_server:app --reload

# 生产模式
uv run uvicorn gcj_rectify_server:app --host 0.0.0.0 --port 8000
```