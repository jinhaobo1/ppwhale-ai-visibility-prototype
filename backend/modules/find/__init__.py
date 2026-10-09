"""模块1：能被找到（10 分）——抓取、索引、站点地图与 URL。

★★ 这是一个「完整示例模块」，其他合作者照着这个结构写自己的模块。★★

约定：
- 入口函数固定为 run(context) -> list[dict]，只读 context，不自己抓取；
- 用 checks.make_check() 构造结果；
- 本模块负责 ID 1-8（见 checks.CHECK_ID_RANGES）。
"""

from urllib.parse import urlparse

from checks import make_check

DIM = 0  # 维度下标（能被找到）


def run(context):
    checks = []
    domain = context.domain
    robots = context.robots
    sitemap = context.sitemap
    llms = context.llms
    home = context.home
    # 可读代表页（含首页），供多页类检查使用
    readable = [p for p in context.pages if p and p.status == 200 and p.text_len > 0]

    # ---- 1. 抓取规则文件 robots.txt ----
    if robots and robots.found:
        checks.append(make_check(1, DIM, "good", "抓取规则文件", 2, 2,
            "robots.txt 可访问。", "保持 robots.txt 可访问并允许公开核心页面被抓取。",
            evidence=[f"{robots.url} | HTTP {robots.status}"]))
    else:
        checks.append(make_check(1, DIM, "warn", "抓取规则文件", 0, 2,
            "未检测到可访问的 robots.txt。", "提供可访问的 robots.txt。", evidence=[]))

    # ---- 2. 站点地图 sitemap ----
    if sitemap.found:
        n = len(sitemap.urls)
        checks.append(make_check(2, DIM, "good", "站点地图", 2, 2,
            f"sitemap 可访问，发现 {n} 个唯一 URL。", "保持 sitemap 可访问、无重复且持续更新。",
            evidence=[f"https://{domain}/sitemap.xml | HTTP 200 | {n} 个 URL"]))
    else:
        checks.append(make_check(2, DIM, "warn", "站点地图", 0, 2,
            "未检测到可访问的 sitemap.xml。", "提供可访问的 sitemap.xml。", evidence=[]))

    # ---- 3. 规范地址一致性 canonical ----
    if readable:
        with_canonical = [p for p in readable if p.canonical]
        ratio = len(with_canonical) / len(readable)
        score = round(2 * ratio)
        status = "good" if ratio >= 0.9 else ("warn" if ratio >= 0.5 else "bad")
        checks.append(make_check(3, DIM, status, "规范地址一致性", score, 2,
            f"{len(with_canonical)}/{len(readable)} 个页面配置了 canonical。",
            "为核心页面提供自引用 canonical。",
            evidence=[p.canonical for p in with_canonical[:3]]))
    else:
        checks.append(make_check(3, DIM, "warn", "规范地址一致性", 0, 2,
            "无页面可读取，无法判定。", "修复页面可访问性后重新检测。", evidence=[]))

    # ---- 4. 页面可索引性 noindex ----
    noindex_pages = [p for p in readable if p.noindex]
    if not noindex_pages:
        checks.append(make_check(4, DIM, "good", "页面可索引性", 1, 1,
            f"{len(readable)} 个页面未发现 noindex/nosnippet。", "保持核心页面可索引。", evidence=[]))
    else:
        checks.append(make_check(4, DIM, "bad", "页面可索引性", 0, 1,
            f"{len(noindex_pages)} 个页面存在 noindex 指令。", "移除核心页面的 noindex。",
            evidence=[p.url for p in noindex_pages[:5]]))

    # ---- 5. 页面可访问性（建议项，不计分）----
    failed = [p for p in context.pages if p and p.status != 200]
    checks.append(make_check(5, DIM, "advice", "页面可访问性", None, None,
        f"共发现 {len(context.pages)} 个代表页，{len(failed)} 个抓取失败。",
        "修复异常状态、重定向链和不可读取的核心页面。",
        evidence=[f"{p.url} | HTTP {p.status}" for p in failed[:5]]))

    # ---- 6. 语义化 URL ----
    semantic_candidates = [p for p in readable if _is_semantic_url(p.url) is not None]
    if semantic_candidates:
        good = [p for p in semantic_candidates if _is_semantic_url(p.url)]
        ratio = len(good) / len(semantic_candidates)
        score = round(2 * ratio)
        status = "good" if ratio >= 0.9 else ("warn" if ratio >= 0.5 else "bad")
        checks.append(make_check(6, DIM, status, "语义化 URL", score, 2,
            f"{len(good)}/{len(semantic_candidates)} 个 URL 使用可读路径。",
            "重要页面使用可读路径，避免纯数字、长哈希或 ID 查询参数。",
            evidence=[p.url for p in semantic_candidates[:3]]))
    else:
        checks.append(make_check(6, DIM, "warn", "语义化 URL", 0, 2,
            "没有足够的 URL 样本判定。", "补充可读路径页面后重新检测。", evidence=[]))

    # ---- 7. HTTPS 交付 ----
    if home and home.final_url and home.final_url.startswith("https://"):
        checks.append(make_check(7, DIM, "good", "HTTPS 交付", 1, 1,
            "网站通过 HTTPS 返回响应。", "所有公开页面使用有效 HTTPS。",
            evidence=[f"{home.final_url} | HTTPS"]))
    else:
        checks.append(make_check(7, DIM, "bad", "HTTPS 交付", 0, 1,
            "网站未通过 HTTPS 返回响应。", "启用有效 HTTPS 证书。", evidence=[]))

    # ---- 8. 机器可读内容目录 llms.txt（建议项，不计分）----
    if llms.found:
        checks.append(make_check(8, DIM, "advice", "机器可读内容目录", None, None,
            "已发现 llms.txt。", "可继续维护机器可读内容目录。",
            evidence=[f"https://{domain}/llms.txt | HTTP {llms.status}"]))
    else:
        checks.append(make_check(8, DIM, "advice", "机器可读内容目录", None, None,
            "未发现 llms.txt。", "建议提供 llms.txt 机器可读内容目录。", evidence=[]))

    return checks


def _is_semantic_url(url: str) -> bool | None:
    """判断 URL 是否语义化。返回 None 表示不参与判定（根路径/语言入口等）。"""
    try:
        path = urlparse(url).path
    except Exception:
        return None
    segments = [s for s in path.split("/") if s]
    if not segments:
        return None  # 根路径不参与
    for s in segments:
        if s.isdigit():          # 纯数字
            return False
        if len(s) > 60:          # 疑似长哈希
            return False
    return True
