"""核心检测逻辑：抓取 → 解析 → 逐项打分 → 汇总成报告。

MVP 已实现（真实检测，单页）：
  - 域名规范化
  - 抓取首页 + robots.txt + sitemap.xml + llms.txt
  - 解析首页 title / meta / h1 / 正文长度 / JSON-LD
  - 8 个基础检查项（HTTPS、robots.txt、sitemap、llms.txt、正文可读、标题摘要、主标题、正文深度、结构化数据）

TODO（后续扩展）：
  - 多页爬取：面包屑标记、文章署名日期、公司/联系/隐私页面、案例页等
  - 更完整的 30 项判定（对应原型的 checks 数组）
"""

import json
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "PPWhale-AI-Visibility-Checker/0.1 (+https://ppwhale.com)"
TIMEOUT = 15.0


# ---------------------------------------------------------------- 抓取与解析

def normalize(raw_url: str) -> str:
    """校验并规范化输入，返回纯域名（不含协议/路径）。非法输入抛 ValueError。"""
    raw_url = (raw_url or "").strip()
    if not raw_url:
        raise ValueError("请输入官网地址，例如 example.com。")
    if not raw_url.startswith(("http://", "https://")):
        raw_url = "https://" + raw_url
    parsed = urlparse(raw_url)
    if not parsed.hostname or "." not in parsed.hostname:
        raise ValueError("请输入有效的官网域名，例如 example.com。")
    return parsed.hostname


async def _get(client: httpx.AsyncClient, url: str):
    """抓取单个 URL，任何异常都返回 None（不中断整体流程）。"""
    try:
        return await client.get(url)
    except Exception:
        return None


async def fetch(domain: str) -> dict:
    """抓取首页 + 关键文件，返回扫描上下文。"""
    base = f"https://{domain}"
    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        home = await _get(client, base + "/")
        robots = await _get(client, base + "/robots.txt")
        sitemap = await _get(client, base + "/sitemap.xml")
        llms = await _get(client, base + "/llms.txt")
    return {"domain": domain, "home": home, "robots": robots, "sitemap": sitemap, "llms": llms}


def parse_home(html: str) -> dict:
    """解析首页 HTML，抽出打分所需的基础信号。"""
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    meta_desc = ""
    m = soup.find("meta", attrs={"name": "description"})
    if m and m.get("content"):
        meta_desc = m["content"].strip()

    h1_count = len(soup.find_all("h1"))

    # 正文长度：去掉 script/style 后的可见文本字符数
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text_len = len(soup.get_text(" ", strip=True))

    # 结构化数据 JSON-LD 类型列表
    schemas: list[str] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for it in items:
                if isinstance(it, dict) and it.get("@type"):
                    schemas.append(it["@type"])
        except Exception:
            pass

    list_count = len(soup.find_all(["ul", "ol"]))
    table_count = len(soup.find_all("table"))

    return {
        "title": title,
        "meta_desc": meta_desc,
        "h1_count": h1_count,
        "text_len": text_len,
        "schemas": schemas,
        "list_count": list_count,
        "table_count": table_count,
    }


# ---------------------------------------------------------------- 检查项

def _check(cid, dim, status, title, score, mx, impact, fix, evidence=None):
    """构造一个检查结果字典（字段与前端原型对齐）。score/mx 为 None 表示「建议项」不计分。"""
    return {
        "id": cid, "dim": dim, "status": status, "title": title,
        "priority": "", "score": score, "max": mx,
        "impact": impact, "fix": fix, "scope": "", "evidence": evidence or [],
    }


def run_checks(fetched: dict, parsed: dict) -> list[dict]:
    """执行检查项。这里只实现单页可真实判定的基础项，其余后续补充。"""
    domain = fetched["domain"]
    home = fetched["home"]
    robots = fetched["robots"]
    sitemap = fetched["sitemap"]
    llms = fetched["llms"]
    checks: list[dict] = []
    cid = 0

    # —— 维度 0 能被找到 (dim=0) ——
    # HTTPS 交付
    if home is not None and str(home.url).startswith("https://"):
        checks.append(_check(cid := cid + 1, 0, "good", "HTTPS 交付", 1, 1,
            "网站通过 HTTPS 返回响应。", "所有公开页面应使用有效 HTTPS。",
            [f"https://{domain}/ | HTTP {home.status_code} | HTTPS"]))
    else:
        checks.append(_check(cid := cid + 1, 0, "bad", "HTTPS 交付", 0, 1,
            "网站未通过 HTTPS 返回响应。", "启用有效 HTTPS 证书。", []))

    # robots.txt 可访问
    if robots is not None and robots.status_code == 200:
        checks.append(_check(cid := cid + 1, 0, "good", "抓取规则文件", 2, 2,
            "robots.txt 可访问。", "保持 robots.txt 可访问。",
            [f"https://{domain}/robots.txt | HTTP 200"]))
    else:
        checks.append(_check(cid := cid + 1, 0, "warn", "抓取规则文件", 0, 2,
            "未检测到可访问的 robots.txt。", "提供可访问的 robots.txt。", []))

    # sitemap 存在
    if sitemap is not None and sitemap.status_code == 200:
        checks.append(_check(cid := cid + 1, 0, "good", "站点地图", 2, 2,
            "sitemap.xml 可访问。", "保持 sitemap 可访问并持续更新。",
            [f"https://{domain}/sitemap.xml | HTTP 200"]))
    else:
        checks.append(_check(cid := cid + 1, 0, "warn", "站点地图", 0, 2,
            "未检测到可访问的 sitemap.xml。", "提供可访问的 sitemap.xml。", []))

    # llms.txt（建议项，不计分）
    if llms is not None and llms.status_code == 200:
        checks.append(_check(cid := cid + 1, 0, "advice", "机器可读内容目录", None, None,
            "已发现 llms.txt。", "可继续维护机器可读内容目录。",
            [f"https://{domain}/llms.txt | HTTP 200"]))
    else:
        checks.append(_check(cid := cid + 1, 0, "advice", "机器可读内容目录", None, None,
            "未发现 llms.txt。", "建议提供 llms.txt 机器可读内容目录。", []))

    # —— 维度 1 能被看见 (dim=1) ——
    if home is not None and home.status_code == 200 and parsed["text_len"] > 0:
        checks.append(_check(cid := cid + 1, 1, "good", "页面内容可读取", 4, 4,
            f"首页返回可读取正文，约 {parsed['text_len']} 字符。", "确保正文可在页面源内容中读取。",
            [f"https://{domain}/ | HTTP {home.status_code} | 正文 {parsed['text_len']} 字符"]))
    else:
        checks.append(_check(cid := cid + 1, 1, "bad", "页面内容可读取", 0, 4,
            "首页未能读取到正文内容。", "修复页面状态，确保正文可读取。", []))

    # 标题与摘要
    title_ok = bool(parsed["title"])
    desc_ok = bool(parsed["meta_desc"])
    if title_ok and desc_ok:
        checks.append(_check(cid := cid + 1, 1, "good", "标题与摘要", 4, 4,
            "标题与页面摘要完整。", "保持唯一、准确的标题和摘要。", []))
    else:
        missing = []
        if not title_ok: missing.append("标题")
        if not desc_ok: missing.append("摘要")
        checks.append(_check(cid := cid + 1, 1, "warn", "标题与摘要", 2, 4,
            f"缺少 {'、'.join(missing)}。", "补充标题和页面摘要。", []))

    # 主标题结构
    if parsed["h1_count"] == 1:
        checks.append(_check(cid := cid + 1, 1, "good", "主标题结构", 3, 3,
            "页面有且仅有一个主标题。", "保持一个清晰主标题。", []))
    else:
        checks.append(_check(cid := cid + 1, 1, "warn", "主标题结构", 1, 3,
            f"检测到 {parsed['h1_count']} 个主标题。", "每页保留一个清晰主标题。", []))

    # 正文信息深度
    if parsed["text_len"] >= 1500:
        checks.append(_check(cid := cid + 1, 1, "good", "正文信息深度", 5, 5,
            f"首页正文约 {parsed['text_len']} 字符，信息较充分。", "保持内容深度。", []))
    elif parsed["text_len"] >= 300:
        checks.append(_check(cid := cid + 1, 1, "warn", "正文信息深度", 3, 5,
            f"首页正文约 {parsed['text_len']} 字符，信息偏少。", "补充定义、规格、场景等内容。", []))
    else:
        checks.append(_check(cid := cid + 1, 1, "bad", "正文信息深度", 1, 5,
            f"首页正文仅 {parsed['text_len']} 字符，信息不足。", "补充正文内容。", []))

    # —— 维度 2 能被理解 (dim=2) ——
    if parsed["schemas"]:
        checks.append(_check(cid := cid + 1, 2, "good", "结构化数据", 4, 4,
            f"检测到结构化数据类型：{', '.join(sorted(set(parsed['schemas'])))}。",
            "保持结构化数据有效。", [f"https://{domain}/ | Schema: " + ", ".join(parsed["schemas"])]))
    else:
        checks.append(_check(cid := cid + 1, 2, "warn", "结构化数据", 0, 4,
            "未检测到 JSON-LD 结构化数据。", "补充品牌/组织/网站等结构化标记。", []))

    # TODO: 维度 3 (能被信任) 与维度 4 (能被引用) 的检查项需要多页爬取或更复杂分析，后续补充。

    return checks


# ---------------------------------------------------------------- 汇总

def build_report(domain: str, checks: list[dict]) -> dict:
    """把检查结果汇总成前端需要的报告结构（五维分数 + 检查项）。"""
    from checks import DIMENSIONS

    dim_scores = [0] * len(DIMENSIONS)
    for c in checks:
        if c["score"] is not None:
            dim_scores[c["dim"]] += c["score"]

    dimensions = [
        {
            "name": d["name"],
            "score": dim_scores[i],
            "max": d["max"],
            "label": d["label"],
        }
        for i, d in enumerate(DIMENSIONS)
    ]
    return {"domain": domain, "dimensions": dimensions, "checks": checks}


async def analyze_website(raw_url: str) -> dict:
    """入口：规范化 → 抓取 → 解析 → 检查 → 汇总报告。"""
    domain = normalize(raw_url)
    fetched = await fetch(domain)
    parsed = parse_home(fetched["home"].text) if fetched["home"] is not None and fetched["home"].status_code == 200 else {
        "title": "", "meta_desc": "", "h1_count": 0, "text_len": 0,
        "schemas": [], "list_count": 0, "table_count": 0,
    }
    checks = run_checks(fetched, parsed)
    return build_report(domain, checks)
