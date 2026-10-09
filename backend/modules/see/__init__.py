"""模块2：能被看见（30 分）——正文读取、标题与内容结构。

负责检查项 ID 9-16（见 checks.CHECK_ID_RANGES["see"]）：
  9  页面内容可读取    10 标题与摘要      11 主标题结构      12 正文信息深度
  13 段落与开篇信息    14 答案型内容结构  15 文章时间信息    16 正文内链与重点标记

约定：
  - 入口 run(context) -> list[dict]，只读 context，不自己抓取；
  - 用 checks.make_check() 构造结果；
  - ID 必须落在 9-16。
"""

from checks import make_check

DIM = 1  # 维度下标（能被看见）


def run(context):
    if context is None:  # 防御：框架签名测试会传 None
        return []

    checks = []
    pages = [p for p in (context.pages or []) if p is not None]
    total = len(pages)
    fetched = [p for p in pages if p.status == 200]
    readable = [p for p in fetched if p.text_len > 0]

    # ---- 9. 页面内容可读取 ----
    if total == 0:
        checks.append(make_check(9, DIM, "bad", "页面内容可读取", 0, 4,
            "未抓取到任何页面。", "确认网站可访问后重新检测。"))
    else:
        ratio = len(readable) / total
        avg = round(sum(p.text_len for p in readable) / len(readable)) if readable else 0
        empty = [p for p in fetched if p.text_len == 0]
        checks.append(make_check(9, DIM, _status(ratio), "页面内容可读取",
            _score(ratio, 4), 4,
            f"{len(readable)}/{total} 个页面返回可读正文，平均 {avg} 字。",
            "确保核心页面直接返回可读文本，避免依赖 JS 渲染。",
            evidence=[f"{p.url} | 正文 {p.text_len} 字" for p in readable[:3]]
                     + [f"{p.url} | 正文为空（疑似 JS 渲染）" for p in empty[:3]]))

    # ---- 10. 标题与摘要 ----
    if not fetched:
        checks.append(make_check(10, DIM, "bad", "标题与摘要", 0, 4,
            "无页面可判定。", "确保页面可访问。"))
    else:
        n = len(fetched)
        title_ok = [p for p in fetched if (p.title or "").strip()]
        desc_ok = [p for p in fetched if (p.meta_desc or "").strip()]
        completeness = (len(title_ok) + len(desc_ok)) / (2 * n)
        dup_titles = _duplicates([(p.title or "").strip() for p in title_ok])
        dup_descs = _duplicates([(p.meta_desc or "").strip() for p in desc_ok])
        score = _score(completeness, 4)
        if dup_titles or dup_descs:
            score = max(0, score - 1)
        status = "good" if (completeness >= 0.9 and not dup_titles and not dup_descs) \
            else ("warn" if completeness >= 0.5 else "bad")
        checks.append(make_check(10, DIM, status, "标题与摘要", score, 4,
            f"{len(title_ok)}/{n} 有 title，{len(desc_ok)}/{n} 有 meta description。",
            "为每个页面撰写唯一且完整的 title 与 description。",
            evidence=[f"重复 title：{t}" for t in dup_titles[:2]]
                     + [f"重复 description：{d}" for d in dup_descs[:2]]
                     + [f"{p.url} | title/description 缺失"
                        for p in fetched[:2] if not (p.title or "").strip() or not (p.meta_desc or "").strip()]))

    # ---- 11. 主标题结构 ----
    if not fetched:
        checks.append(make_check(11, DIM, "bad", "主标题结构", 0, 3,
            "无页面可判定。", "确保页面可访问。"))
    else:
        n = len(fetched)
        one_h1 = [p for p in fetched if p.h1_count == 1]
        ratio = len(one_h1) / n
        checks.append(make_check(11, DIM, _status(ratio), "主标题结构",
            _score(ratio, 3), 3,
            f"{len(one_h1)}/{n} 个页面恰好 1 个 H1。",
            "每个页面保持唯一 H1 主标题。",
            evidence=[f"{p.url} | H1={p.h1_count}" for p in fetched if p.h1_count != 1][:5]))

    # ---- 12. 正文信息深度 ----
    if not readable:
        checks.append(make_check(12, DIM, "bad", "正文信息深度", 0, 5,
            "无页面返回可读正文。", "确保页面返回可读文本。"))
    else:
        avg = sum(p.text_len for p in readable) / len(readable)
        mn = min(p.text_len for p in readable)
        mx = max(p.text_len for p in readable)
        if avg >= 1000:
            score, status = 5, "good"
        elif avg >= 600:
            score, status = 4, "good"
        elif avg >= 300:
            score, status = 3, "warn"
        elif avg >= 150:
            score, status = 2, "warn"
        elif avg >= 50:
            score, status = 1, "bad"
        else:
            score, status = 0, "bad"
        checks.append(make_check(12, DIM, status, "正文信息深度", score, 5,
            f"代表页平均正文 {avg:.0f} 字（{mn}~{mx}）。",
            "扩充核心页面正文，提供更完整的说明内容。",
            evidence=[f"平均 {avg:.0f} 字 | 共 {len(readable)} 页"]))

    # ---- 13. 段落与开篇信息 ----
    if not fetched:
        checks.append(make_check(13, DIM, "bad", "段落与开篇信息", 0, 4,
            "无页面可判定。", "确保页面可访问。"))
    else:
        n = len(fetched)
        substantive = [p for p in fetched if p.p_count >= 1 and p.text_len >= 200]
        ratio = len(substantive) / n
        avg_p = round(sum(p.p_count for p in fetched) / n, 1)
        checks.append(make_check(13, DIM, _status(ratio), "段落与开篇信息",
            _score(ratio, 4), 4,
            f"{len(substantive)}/{n} 个页面开篇有实质文本，平均 {avg_p} 个段落。",
            "用段落组织正文，开篇即给出实质信息。",
            evidence=[f"{p.url} | 段落 {p.p_count} | 正文 {p.text_len} 字" for p in fetched[:3]]))

    # ---- 14. 答案型内容结构 ----
    if not fetched:
        checks.append(make_check(14, DIM, "bad", "答案型内容结构", 0, 4,
            "无页面可判定。", "确保页面可访问。"))
    else:
        n = len(fetched)
        structured = [p for p in fetched
                      if p.table_count or p.dl_count or p.question_headings or p.list_count >= 2]
        ratio = len(structured) / n
        checks.append(make_check(14, DIM, _status(ratio), "答案型内容结构",
            _score(ratio, 4), 4,
            f"{len(structured)}/{n} 个页面包含列表/表格/定义列表/问答标题。",
            "用列表、表格、问答式标题组织答案型内容。",
            evidence=[f"{p.url} | 列表 {p.list_count} | 表格 {p.table_count} | 问答 {p.question_headings}"
                      for p in structured[:3]]))

    # ---- 15. 文章时间信息 ----
    if not fetched:
        checks.append(make_check(15, DIM, "bad", "文章时间信息", 0, 3,
            "无页面可判定。", "确保页面可访问。"))
    else:
        n = len(fetched)
        timed = [p for p in fetched if p.time_elems or p.visible_date or p.jsonld_dates]
        ratio = len(timed) / n
        checks.append(make_check(15, DIM, _status(ratio), "文章时间信息",
            _score(ratio, 3), 3,
            f"{len(timed)}/{n} 个页面包含时间信息（<time>/可见日期/JSON-LD 日期）。",
            "在文章页标注发布时间或更新日期。",
            evidence=[f"{p.url} | <time> {p.time_elems} | JSON-LD 日期 {len(p.jsonld_dates)}"
                      for p in timed[:3]]))

    # ---- 16. 正文内链与重点标记 ----
    if not fetched:
        checks.append(make_check(16, DIM, "bad", "正文内链与重点标记", 0, 3,
            "无页面可判定。", "确保页面可访问。"))
    else:
        n = len(fetched)
        linked = [p for p in fetched if p.internal_links >= 2 and p.strong_count >= 1]
        ratio = len(linked) / n
        checks.append(make_check(16, DIM, _status(ratio), "正文内链与重点标记",
            _score(ratio, 3), 3,
            f"{len(linked)}/{n} 个页面正文含站内链接与重点标记。",
            "在正文中添加站内链接，并用加粗/强调标记重点。",
            evidence=[f"{p.url} | 站内链接 {p.internal_links} | 重点 {p.strong_count}"
                      for p in fetched[:3]]))

    return checks


def _status(ratio):
    """比例 → 状态：≥0.9 通过，≥0.5 部分满足，否则问题。"""
    return "good" if ratio >= 0.9 else ("warn" if ratio >= 0.5 else "bad")


def _score(ratio, mx):
    """按比例折算分数（四舍五入，不超满分）。"""
    return int(mx * ratio + 0.5)


def _duplicates(values):
    """返回出现次数大于 1 的值列表（去重）。"""
    seen, dup = set(), set()
    for v in values:
        if v in seen:
            dup.add(v)
        seen.add(v)
    return sorted(dup)
