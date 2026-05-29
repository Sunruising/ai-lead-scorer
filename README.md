# AI 销售线索打分助手（lead-scorer）

提交一条销售线索（公司 / 需求 / 预算 / 联系方式等），由大模型按预设规则自动打分（0-100）、分级（高 / 中 / 低意向）、给出打分理由和下一步跟进建议，高意向线索标记为「需立即跟进」。
适用场景：B2B 销售线索分流、市场获客后的自动分级、CRM 线索质量评估。

## 技术栈
- **后端**：FastAPI
- **大模型**：DeepSeek（`deepseek-chat`，OpenAI 兼容接口，纯 LLM）
- **前端**：原生 HTML/JS
- **依赖管理**：uv

## 特性
- 高意向线索（预算足、决策人、需求清晰、时间紧）给高分并标记立即跟进；信息缺失、随便问问的线索给低分。
- 每次打分给出 2-4 条理由和一句话下一步建议，结果可解释。
- 打分维度集中在 `app/scorer.py`，可按业务调整权重与阈值。

---

## 运行

### 1. 配置 DeepSeek Key
把 `.env.example` 复制成 `.env`，填入 key：
```
DEEPSEEK_API_KEY=sk-你的key
```

### 2. 安装依赖并启动（uv）
```bash
cd ~/pyProjects/ai-lead-scorer
uv venv --python 3.12
uv pip install -r requirements.txt
uv run uvicorn app.main:app --reload --port 8001
```

### 3. 浏览器访问
打开 http://127.0.0.1:8001
- 填表单（公司、需求、预算、是否决策人、时间、联系方式）后点「开始打分」
- `samples/leads.json` 提供三条不同质量的示例线索可直接调用接口测试

### 4. 用 curl 调接口
```bash
curl -s -X POST http://127.0.0.1:8001/api/score \
  -H "Content-Type: application/json" \
  -d '{"company":"星辰智能制造","requirement":"上设备预测性维护系统，对接MES","budget":"80万","is_decision_maker":true,"timeline":"本季度签约","contact":"张总 13800001111"}'
```
返回示例：
```json
{
  "score": 88,
  "tier": "高",
  "reasons": ["预算80万明确且可观", "联系人为CTO是决策人", "需求清晰、时间紧迫"],
  "next_action": "24小时内电话联系张总，安排方案演示并报价",
  "need_immediate_follow_up": true
}
```

---

## 打分规则说明
打分规则集中写在 `app/scorer.py` 的 `SCORING_RULES` 里，会被注入到大模型的 system prompt 作为评估依据：

**加分项**
- 预算充足且明确（强加分）
- 需求描述清晰具体
- 联系人是决策人（强加分）
- 时间紧迫、有明确上线/采购时间点
- 公司规模大或处于扩张期
- 联系方式齐全（小幅加分）

**减分项**
- 需求模糊、随便问问、无预算或预算极低
- 联系人无决策权
- 信息严重缺失（大幅减分）

**分级阈值**（在 `scorer.py` 中可调）
- `score >= 70` → 高意向（标记需立即跟进）
- `40 <= score < 70` → 中意向
- `score < 40` → 低意向

> 最终分数由大模型综合判断给出，规则作为指引注入 prompt；代码层面再以分数为准重新校正 tier，避免分数与分级不一致。

---

## 目录结构
```
ai-lead-scorer/
├── app/
│   ├── main.py            # FastAPI 接口 + 托管前端
│   ├── scorer.py          # 打分核心：构造 prompt → 调 DeepSeek → 解析 JSON → 容错
│   └── static/index.html  # 表单页面
├── samples/
│   └── leads.json         # 3 条不同质量的示例线索
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 可拓展方向
- 批量打分接口（一次传多条线索，返回排序后的优先跟进列表）
- 对接 CRM（销售易 / HubSpot / 企业微信）自动回写分数与跟进任务
- 打分规则做成配置文件 / 后台可视化编辑，无需改代码
- 加历史数据微调权重、用真实成交结果反向校准评分模型
- 高意向线索自动触发通知（企业微信 / 飞书机器人 / 短信）
- 多维度雷达图展示线索画像
