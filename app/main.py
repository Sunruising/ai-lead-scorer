"""
FastAPI 服务入口。

- GET  /            返回表单页面。
- POST /api/score   接收一条销售线索 JSON，返回打分结果。
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.scorer import score_lead

# 加载项目根目录下的 .env（DEEPSEEK_API_KEY 等）
load_dotenv()

app = FastAPI(title="AI 销售线索打分助手", description="提交线索，自动打分分级并给出跟进建议")

STATIC_DIR = Path(__file__).parent / "static"


class Lead(BaseModel):
    """销售线索入参模型。字段均可选，模型会根据已有信息综合打分。"""

    company: str = Field("", description="公司名称")
    requirement: str = Field("", description="需求描述")
    budget: str = Field("", description="预算（可填金额或区间）")
    is_decision_maker: bool = Field(False, description="联系人是否为决策人")
    timeline: str = Field("", description="时间要求 / 上线时间点")
    contact: str = Field("", description="联系方式（电话/微信/邮箱）")
    notes: str = Field("", description="其他备注信息")


@app.get("/")
def index() -> FileResponse:
    """返回表单页面。"""
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/score")
def api_score(lead: Lead) -> dict:
    """对提交的线索打分并返回结构化结果。"""
    # 只把有值的字段传给打分核心，避免大量空字段干扰模型判断
    lead_dict = {k: v for k, v in lead.model_dump().items() if v not in ("", False)}
    result = score_lead(lead_dict)
    return result
