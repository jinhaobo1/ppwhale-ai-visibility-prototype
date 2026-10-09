"""FastAPI 入口：提供 POST /api/check 检测接口。

本地启动：
    cd backend
    .venv\\Scripts\\activate
    uvicorn main:app --reload --port 8000

测试：
    curl -X POST http://127.0.0.1:8000/api/check -H "Content-Type: application/json" -d '{"url":"ppwhale.com"}'
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine import analyze

app = FastAPI(title="PPWhale 官网 AI 信源诊断")

# 允许跨域（前端以 file:// 打开时 Origin 为 null，这里放开全部）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CheckRequest(BaseModel):
    url: str


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/check")
async def check(req: CheckRequest):
    """核心检测接口：输入域名/URL，返回五维评分 + 检查项报告。"""
    try:
        return await analyze(req.url)
    except ValueError as e:
        return {"error": str(e)}
