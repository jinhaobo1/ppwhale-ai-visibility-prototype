"""维度 3「能被理解」的 AI 增强（DeepSeek，可选）。

职责：把规则引擎算好的检查结果喂给 DeepSeek，让 AI 生成
  - 每项更具体的「问题解读」与「优化建议」（附加为 ai_impact / ai_fix 字段，不改动规则字段）
  - 一段维度总评（由调用方追加为建议项）

规则：
  - **纯增强，不改分**：分数/状态/证据全部由规则引擎决定，AI 只补充文案；
  - **可降级**：未配置 DEEPSEEK_API_KEY、超时、接口报错、返回解析失败时，
    静默退回纯规则模式，绝不抛异常；
  - 只依赖 httpx（框架已有依赖），同步调用（模块 run() 由框架同步调用）。

配置（环境变量）：
  - DEEPSEEK_API_KEY   必填，不填则 AI 增强关闭
  - DEEPSEEK_BASE_URL  可选，默认 https://api.deepseek.com
  - DEEPSEEK_MODEL     可选，默认 deepseek-chat
"""

import json
import os

import httpx

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"
TIMEOUT = 60.0          # 整个请求超时（秒）
MAX_TOKENS = 1200

# 每项检查中喂给 AI 的字段（不含内部字段，保持 prompt 精简）
_PROMPT_FIELDS = ("id", "title", "status", "score", "impact", "evidence")

_PROMPT_TEMPLATE = """你是品牌 AI 可见度优化专家。下面是网站 {domain}「{dim_name}」维度的 5 项自动检测结果（规则打分，分数不要改动）。
请基于每项的证据，用中文给出：
1. items：每项一段更具体的「问题解读」（ai_impact，50 字内）与一条可执行的「优化建议」（ai_fix，60 字内）；
2. summary：一段维度总评（120 字内，先讲现状，再点出最重要的一步行动）。
只输出 JSON，格式：{{"items": {{"<检查项id>": {{"ai_impact": "...", "ai_fix": "..."}}}}, "summary": "..."}}

检测结果：
{checks_json}"""


def _enabled() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())


def _api_payload(domain: str, dim_name: str, checks: list[dict]) -> dict:
    """构造请求体。"""
    slim = [{k: c.get(k) for k in _PROMPT_FIELDS} for c in checks]
    prompt = _PROMPT_TEMPLATE.format(
        domain=domain,
        dim_name=dim_name,
        checks_json=json.dumps(slim, ensure_ascii=False, indent=1),
    )
    return {
        "model": os.environ.get("DEEPSEEK_MODEL", MODEL),
        "messages": [
            {"role": "system", "content": "你只输出一个合法 JSON 对象，不要输出任何其他文字或代码块标记。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": MAX_TOKENS,
        "response_format": {"type": "json_object"},
        "stream": False,
    }


def _parse_content(content: str) -> dict | None:
    """解析模型返回的 JSON（容忍代码块标记与首尾空白）。"""
    if not content:
        return None
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def enhance(domain: str, dim_name: str, checks: list[dict]) -> tuple[list[dict], str | None]:
    """AI 增强入口。

    返回 (checks, summary)：
      - checks：原列表原地追加 ai_impact / ai_fix 字段（解析成功时）；
      - summary：维度总评文本；任何失败返回 None。
    无论成败都不抛异常，保证框架稳定。
    """
    if not _enabled():
        return checks, None
    base_url = os.environ.get("DEEPSEEK_BASE_URL", BASE_URL).rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY'].strip()}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(url, headers=headers,
                               json=_api_payload(domain, dim_name, checks))
        if resp.status_code != 200:
            return checks, None
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    except Exception:
        return checks, None

    parsed = _parse_content(content)
    if not parsed:
        return checks, None

    items = parsed.get("items")
    if isinstance(items, dict):
        by_id = {c["id"]: c for c in checks}
        for key, val in items.items():
            try:
                cid = int(key)
            except (TypeError, ValueError):
                continue
            check = by_id.get(cid)
            if not check or not isinstance(val, dict):
                continue
            ai_impact = val.get("ai_impact")
            ai_fix = val.get("ai_fix")
            if isinstance(ai_impact, str) and ai_impact.strip():
                check["ai_impact"] = ai_impact.strip()
            if isinstance(ai_fix, str) and ai_fix.strip():
                check["ai_fix"] = ai_fix.strip()

    summary = parsed.get("summary")
    return checks, (summary.strip() if isinstance(summary, str) and summary.strip() else None)
