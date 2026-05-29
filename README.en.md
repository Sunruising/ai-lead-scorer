**English** | [简体中文](./README.md)

# AI Lead Scorer (lead-scorer)

Submit a sales lead (company / requirement / budget / contact, etc.) and an LLM scores it automatically against preset rules: a score (0-100), a tier (high / medium / low intent), the reasoning behind the score, and a suggested next action. High-intent leads are flagged as "follow up immediately".
Use cases: B2B lead triage, automatic tiering of leads after marketing campaigns, CRM lead-quality assessment.

## Tech Stack
- **Backend**: FastAPI
- **LLM**: DeepSeek (`deepseek-chat`, OpenAI-compatible API, pure LLM)
- **Frontend**: vanilla HTML/JS
- **Dependency management**: uv

## Features
- High-intent leads (sufficient budget, decision maker, clear requirement, tight timeline) get high scores and are flagged for immediate follow-up; leads with missing info or casual inquiries get low scores.
- Every score comes with 2-4 reasons and a one-line next-action suggestion, so the result is explainable.
- Scoring dimensions live in `app/scorer.py`, so weights and thresholds can be tuned to your business.

---

## Running

### 1. Configure the DeepSeek key
Copy `.env.example` to `.env` and fill in your key:
```
DEEPSEEK_API_KEY=sk-your-key
```

### 2. Install dependencies and start (uv)
```bash
cd ~/pyProjects/ai-lead-scorer
uv venv --python 3.12
uv pip install -r requirements.txt
uv run uvicorn app.main:app --reload --port 8001
```

### 3. Open in the browser
Go to http://127.0.0.1:8001
- Fill in the form (company, requirement, budget, decision maker, timeline, contact) and click "Score".
- `samples/leads.json` provides three sample leads of varying quality that you can send to the API directly for testing.

### 4. Call the API with curl
```bash
curl -s -X POST http://127.0.0.1:8001/api/score \
  -H "Content-Type: application/json" \
  -d '{"company":"星辰智能制造","requirement":"上设备预测性维护系统，对接MES","budget":"80万","is_decision_maker":true,"timeline":"本季度签约","contact":"张总 13800001111"}'
```
Example response:
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

## Scoring Rules
The scoring rules live in `SCORING_RULES` in `app/scorer.py` and are injected into the LLM's system prompt as the evaluation basis:

**Positive factors**
- Sufficient and clearly stated budget (strong boost)
- Clear, specific requirement description
- Contact is a decision maker (strong boost)
- Tight timeline with a concrete go-live / purchase date
- Large or rapidly growing company
- Complete contact details (minor boost)

**Negative factors**
- Vague requirement, casual inquiry, no budget or extremely low budget
- Contact has no decision-making authority
- Severely missing information (heavy penalty)

**Tier thresholds** (tunable in `scorer.py`)
- `score >= 70` → high intent (flagged for immediate follow-up)
- `40 <= score < 70` → medium intent
- `score < 40` → low intent

> The final score is produced by the LLM's overall judgment, with the rules injected into the prompt as guidance; the code then re-derives the tier from the score to avoid any mismatch between score and tier.

---

## Project Structure
```
ai-lead-scorer/
├── app/
│   ├── main.py            # FastAPI endpoints + serves the frontend
│   ├── scorer.py          # Scoring core: build prompt → call DeepSeek → parse JSON → fault-tolerance
│   └── static/index.html  # Form page
├── samples/
│   └── leads.json         # 3 sample leads of varying quality
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Roadmap
- Batch scoring endpoint (submit multiple leads at once, return a prioritized follow-up list sorted by score)
- CRM integration (Xiaoshouyi / HubSpot / WeCom) to write scores and follow-up tasks back automatically
- Move scoring rules into a config file / visual admin editor, no code changes required
- Fine-tune weights with historical data and recalibrate the scoring model against real deal outcomes
- Auto-trigger notifications for high-intent leads (WeCom / Feishu bot / SMS)
- Multi-dimensional radar chart to visualize the lead profile
