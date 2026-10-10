"""模块4：能被信任（15 分）——公司、联系、合规与署名信息。

检查项（ID 22-26，见 docs/spec.md）：
  22 品牌信息完整性  4 分  品牌身份字段在 schema 与页面间是否齐全一致
  23 公司与联系页面  3 分  发现并确认公司/联系页可读、含联系方式
  24 隐私与服务条款  2 分  发现并确认隐私/条款/合规页可读
  25 文章署名与日期  3 分  文章页作者+日期，对照 JSON-LD author/datePublished
  26 官方账号关联    3 分  Organization/Brand 的 sameAs、官方账号链接

规则：
  - 入口 run(context) -> list[dict]，只读 context，不自己抓取；
  - 特定页面（公司/联系/隐私等）通过 context.discovered_urls 与已抓取页面匹配；
  - 评分用离散判定规则；每个检查项始终返回。
"""

import re
from urllib.parse import urlparse

from checks import make_check
from modules.understand import ai as _ai   # 复用维度3模块内的 AI 增强客户端（同属我负责的部分）

DIM = 3  # 维度下标（能被信任）

BRAND_TYPES = {"Organization", "Brand"}
ARTICLE_TYPES = {"BlogPosting", "Article", "NewsArticle", "TechArticle", "Report"}
ARTICLE_URL_KW = ["/blog", "/news", "/article", "/post", "/insight", "/story",
                  "/wiki", "博客", "新闻", "资讯", "文章", "动态"]

COMPANY_KW = ["about", "company", "about-us", "aboutus", "profile",
              "who-we-are", "关于", "公司", "我们", "简介"]
CONTACT_KW = ["contact", "contact-us", "contactus", "联系", "联络", "洽谈", "合作"]
PRIVACY_KW = ["privacy", "隐私"]
TERMS_KW = ["terms", "agreement", "tos", "条款", "协议", "用户协议", "服务协议"]

SOCIAL_DOMAINS = [
    "facebook.com", "x.com", "twitter.com", "instagram.com", "linkedin.com",
    "youtube.com", "youtu.be", "tiktok.com", "pinterest.com", "reddit.com",
    "weibo.com", "weixin.qq.com", "mp.weixin.qq.com", "xiaohongshu.com",
    "douyin.com", "bilibili.com", "zhihu.com", "kuaishou.com",
    "vimeo.com", "twitch.tv", "discord.gg", "t.me",
]

READABLE_MIN_TEXT = 150   # 「页面可读」的正文长度下限（字符）


# ---------------------------------------------------------------------------
# 通用辅助
# ---------------------------------------------------------------------------

def _type_set(node) -> set[str]:
    t = node.get("@type") if isinstance(node, dict) else None
    if isinstance(t, str):
        return {t}
    if isinstance(t, list):
        return {x for x in t if isinstance(x, str)}
    return set()


def _get(node, *keys):
    if not isinstance(node, dict):
        return None
    for k in keys:
        v = node.get(k)
        if isinstance(v, list):
            v = v[0] if v else None
        if v:
            if isinstance(v, dict):
                u = v.get("url") or v.get("@id") or v.get("contentUrl")
                if u:
                    return u
                continue
            return v
    return None


def _brand_nodes(pages) -> list:
    out = []
    for p in pages:
        for n in p.jsonld:
            if _type_set(n) & BRAND_TYPES:
                out.append(n)
    return out


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _url_host(url) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def _host_matches(domain: str, url) -> bool:
    """URL 主机是否属于目标域名（精确匹配域名或其子域，排除 'xxexample.com' 误判）。"""
    host = _url_host(url)
    if not host:
        return False
    domain = (domain or "").lower().lstrip("www.")
    host = host.lower().lstrip("www.")
    return host == domain or host.endswith("." + domain)


def _keyword_hit(url, title, kws) -> bool:
    hay = _norm(url) + " " + _norm(title)
    return any(k in hay for k in kws)


def _fetchable(pages, kws) -> list:
    """已抓取页面中 URL 命中关键词的页面（只看 URL，避免标题误伤）。"""
    return [p for p in pages if _keyword_hit(p.url or "", "", kws)]


def _discovered_hit(context, pages, kws):
    """已发现（未抓取）的候选 URL 中命中关键词的数量。"""
    fetched = {p.url for p in pages}
    n = 0
    for u in context.discovered_urls:
        if u in fetched:
            continue
        if _keyword_hit(u, "", kws):
            n += 1
    return n


def _readable(p) -> bool:
    """页面可读：HTTP 200 且正文长度达标。"""
    return bool(p) and p.status == 200 and (p.text_len or 0) >= READABLE_MIN_TEXT


# ---------------------------------------------------------------------------
# ID 22 品牌信息完整性（4 分）
# ---------------------------------------------------------------------------

def _check22(context, pages):
    nodes = _brand_nodes(pages)
    if not nodes:
        return make_check(22, DIM, "bad", "品牌信息完整性", 0, 4,
            "无 Organization/Brand 结构化标记，品牌身份无法被 AI 对齐到页面信息。",
            "添加 Organization/Brand JSON-LD，并保证与页面 og:site_name、标题一致。",
            evidence=[f"{context.domain}：未发现品牌实体标记"])

    home = context.home
    page_name = ""
    if home and home.og_site_name:
        page_name = _norm(home.og_site_name)
    elif home and home.title:
        page_name = _norm(re.split(r"\s[-–—|]\s", home.title)[0])
    else:
        page_name = _norm(context.domain)

    def _fields_of(node):
        schema_name = _norm(_get(node, "name"))
        schema_url = _get(node, "url", "@id") or ""
        logo = bool(_get(node, "logo"))
        # 名称一致：完全相等，或双方都 ≥2 字符时互为子串（避免 "a" in "abc" 这类误判）
        name_ok = bool(schema_name and page_name
                       and (schema_name == page_name
                            or (len(schema_name) >= 2 and len(page_name) >= 2
                                and (schema_name in page_name or page_name in schema_name))))
        url_ok = bool(schema_url and _host_matches(context.domain, schema_url))
        site_name_ok = bool(home and home.og_site_name)
        return {
            "名称一致": name_ok,
            "URL一致": url_ok,
            "logo": logo,
            "页面og:site_name": site_name_ok,
        }

    # 取全站最完整的品牌实体判定，避免页面顺序影响分数
    best_fields, best_node = {}, None
    for node in nodes:
        fields = _fields_of(node)
        if sum(fields.values()) > sum(best_fields.values()):
            best_fields, best_node = fields, node
    schema_name = _norm(_get(best_node, "name"))
    schema_url = _get(best_node, "url", "@id") or ""
    logo_ok = bool(best_fields.get("logo"))
    site_name_ok = bool(best_fields.get("页面og:site_name"))

    got = [k for k, v in best_fields.items() if v]
    missing = [k for k, v in best_fields.items() if not v]
    score = max(1, len(got))
    status = "good" if score == 4 else ("warn" if score >= 2 else "bad")
    impact = f"品牌实体与页面身份 {len(got)}/4 项齐全一致"
    if missing:
        impact += f"（不一致/缺失：{'、'.join(missing)}）"
    fix = ("保持现状。" if score == 4 else
           f"修复不一致/缺失项：{'、'.join(missing)}——"
           "schema name 与 og:site_name/标题保持一致、url 指向官网、"
           "补 logo，并在页面声明 og:site_name。")
    return make_check(22, DIM, status, "品牌信息完整性", score, 4, impact, fix,
        evidence=[f"schema name={schema_name or '(空)'}，页面身份={page_name or '(空)'}，"
                  f"schema url={schema_url or '(空)'}，logo={'有' if logo_ok else '无'}，"
                  f"og:site_name={'有' if site_name_ok else '无'}",
                  f"共检测到 {len(nodes)} 个品牌实体节点，按最完整者计分"])


# ---------------------------------------------------------------------------
# ID 23 公司与联系页面（3 分）
# ---------------------------------------------------------------------------

def _check23(context, pages):
    home = context.home
    c_pages = _fetchable(pages, COMPANY_KW)
    t_pages = _fetchable(pages, CONTACT_KW)
    targets = c_pages + t_pages

    confirmed = [p for p in targets if _readable(p)
                 and (p.emails or p.phones)]
    readable_only = [p for p in targets if _readable(p)
                     and not (p.emails or p.phones)]
    link_only = (_discovered_hit(context, pages, COMPANY_KW)
                 + _discovered_hit(context, pages, CONTACT_KW))

    if confirmed:
        best = confirmed[0]
        return make_check(23, DIM, "good", "公司与联系页面", 3, 3,
            f"发现可读的公司/联系页面（{best.url}），且含邮箱/电话等联系方式。",
            "保持现状；建议同时在 JSON-LD 中声明 contactPoint。",
            evidence=[f"{best.url}：正文 {best.text_len} 字符，"
                      f"邮箱 {len(best.emails)} 个、电话 {len(best.phones)} 个"])
    if readable_only:
        best = readable_only[0]
        return make_check(23, DIM, "warn", "公司与联系页面", 2, 3,
            f"发现公司/联系页面（{best.url}）且可读，但未检测到邮箱/电话等联系方式。",
            "在公司/联系页显著位置写明邮箱、电话或地址。",
            evidence=[f"{best.url}：正文 {best.text_len} 字符，未检出联系方式"])
    if home and _readable(home) and (home.emails or home.phones):
        return make_check(23, DIM, "warn", "公司与联系页面", 2, 3,
            "未发现独立的公司/联系页面，但首页可见邮箱/电话。",
            "建议增设独立的「关于我们」与「联系我们」页面，方便 AI 抓取引用。",
            evidence=[f"首页含邮箱 {len(home.emails)} 个、电话 {len(home.phones)} 个"])
    if link_only:
        return make_check(23, DIM, "warn", "公司与联系页面", 1, 3,
            f"发现 {link_only} 个公司/联系相关链接，但未被抓取验证。",
            "确保公司/联系页可被抓取（不被 robots 拦截），并补充联系方式。",
            evidence=["发现候选链接但未进入代表页抓取范围"])
    return make_check(23, DIM, "bad", "公司与联系页面", 0, 3,
        "未发现公司或联系页面，AI 无法核实品牌背后的主体。",
        "增设「关于我们」与「联系我们」页面，含公司全称、邮箱、电话、地址。",
        evidence=[f"{context.domain}：未发现公司/联系页面"])


# ---------------------------------------------------------------------------
# ID 24 隐私与服务条款（2 分）
# ---------------------------------------------------------------------------

def _check24(context, pages):
    p_confirmed = [p for p in _fetchable(pages, PRIVACY_KW) if _readable(p)]
    t_confirmed = [p for p in _fetchable(pages, TERMS_KW) if _readable(p)]
    p_discovered = _discovered_hit(context, pages, PRIVACY_KW)
    t_discovered = _discovered_hit(context, pages, TERMS_KW)

    if p_confirmed and t_confirmed:
        return make_check(24, DIM, "good", "隐私与服务条款", 2, 2,
            "隐私政策与服务条款页面均可读。",
            "保持现状；在 JSON-LD 中可补充 publisher 信息关联公司主体。",
            evidence=[f"隐私页：{p_confirmed[0].url}；条款页：{t_confirmed[0].url}"])
    if p_confirmed or t_confirmed or p_discovered or t_discovered:
        parts = []
        if p_confirmed:
            parts.append("隐私页可读")
        elif p_discovered:
            parts.append("发现隐私页链接")
        if t_confirmed:
            parts.append("条款页可读")
        elif t_discovered:
            parts.append("发现条款页链接")
        return make_check(24, DIM, "warn", "隐私与服务条款", 1, 2,
            "隐私政策或服务条款不完整：" + "；".join(parts) + "。",
            "补齐缺失的隐私政策/服务条款页面，并保证可被抓取。",
            evidence=parts)
    return make_check(24, DIM, "bad", "隐私与服务条款", 0, 2,
        "未发现隐私政策或服务条款页面，AI 判定品牌合规透明度不足。",
        "发布隐私政策与服务条款页面，并在页脚链接。",
        evidence=[f"{context.domain}：未发现隐私/条款页面"])


# ---------------------------------------------------------------------------
# ID 25 文章署名与日期（3 分）
# ---------------------------------------------------------------------------

def _is_article(p) -> bool:
    jt = set()
    for n in p.jsonld:
        jt |= _type_set(n)
    if jt & ARTICLE_TYPES:
        return True
    if any(k in _norm(p.url) for k in ARTICLE_URL_KW):
        return True
    return p.time_elems > 0 and p.author_elems > 0


def _has_jsonld_author(p) -> bool:
    return any("author" in n for n in p.jsonld if isinstance(n, dict))


def _has_jsonld_date(p) -> bool:
    return any(("datePublished" in n or "dateModified" in n)
               for n in p.jsonld if isinstance(n, dict))


def _check25(context, pages):
    articles = [p for p in pages if _is_article(p)]
    if not articles:
        return make_check(25, DIM, "warn", "文章署名与日期", 0, 3,
            "未检测到文章页，无法验证署名与日期。",
            "若有博客/资讯内容，请保证文章页可被抓取。",
            evidence=[f"{context.domain}：未发现文章页"])
    covered = 0
    detail = []
    for p in articles:
        author = p.author_elems > 0 or _has_jsonld_author(p)
        date = p.time_elems > 0 or _has_jsonld_date(p)
        if author and date:
            covered += 1
        detail.append(f"{p.url}：作者={'有' if author else '缺'}，"
                      f"日期={'有' if date else '缺'}")
    if covered == len(articles):
        return make_check(25, DIM, "good", "文章署名与日期", 3, 3,
            f"{covered}/{len(articles)} 篇文章均有作者署名与发布日期。",
            "保持现状。", evidence=detail)
    if covered * 2 >= len(articles):
        return make_check(25, DIM, "warn", "文章署名与日期", 2, 3,
            f"{covered}/{len(articles)} 篇文章有署名+日期，其余缺失。",
            "为缺署名/日期的文章补充作者与发布时间（含 JSON-LD datePublished）。",
            evidence=detail)
    if covered > 0:
        return make_check(25, DIM, "warn", "文章署名与日期", 1, 3,
            f"仅 {covered}/{len(articles)} 篇文章有署名+日期。",
            "统一为文章添加作者与发布时间。", evidence=detail)
    return make_check(25, DIM, "bad", "文章署名与日期", 0, 3,
        f"{len(articles)} 篇文章均无署名或日期，AI 难以判断内容可信度。",
        "为文章添加作者署名、发布时间，并在 BlogPosting 中声明 author/datePublished。",
        evidence=detail)


# ---------------------------------------------------------------------------
# ID 26 官方账号关联（3 分）
# ---------------------------------------------------------------------------

def _is_social(url) -> bool:
    """URL 主机是否为官方社媒平台（精确域名/子域匹配，排除 'x.com.evil.com' 误判）。"""
    host = _url_host(url)
    if not host:
        return False
    host = host.lower().lstrip("www.")
    return any(host == d or host.endswith("." + d) for d in SOCIAL_DOMAINS)


def _check26(context, pages):
    sameas_hits = []
    for n in _brand_nodes(pages):
        sa = n.get("sameAs")
        if isinstance(sa, str):
            sa = [sa]
        if isinstance(sa, list):
            for u in sa:
                if isinstance(u, str) and _is_social(u):
                    sameas_hits.append(u)

    link_hits = []
    seen = set()
    for p in pages:
        for u in p.external_links:
            if _is_social(u) and u not in seen:
                seen.add(u)
                link_hits.append(u)

    if sameas_hits and link_hits:
        return make_check(26, DIM, "good", "官方账号关联", 3, 3,
            f"sameAs 声明 {len(sameas_hits)} 个官方账号，页面可见 {len(link_hits)} 个官方链接，互相印证。",
            "保持现状，新增平台时同步更新。",
            evidence=[f"sameAs：{sameas_hits[0]} 等 {len(sameas_hits)} 个；"
                      f"页面链接：{link_hits[0]} 等 {len(link_hits)} 个"])
    if sameas_hits:
        return make_check(26, DIM, "warn", "官方账号关联", 2, 3,
            f"JSON-LD sameAs 声明了 {len(sameas_hits)} 个官方账号，但页面未检测到对应链接。",
            "在页脚等处放置官方账号链接，与 sameAs 保持一致。",
            evidence=[f"sameAs：{sameas_hits[0]} 等 {len(sameas_hits)} 个"])
    if link_hits:
        return make_check(26, DIM, "warn", "官方账号关联", 1, 3,
            f"页面可见 {len(link_hits)} 个官方账号链接，但 JSON-LD 未声明 sameAs。",
            "在 Organization 标记中添加 sameAs 数组，列出官方账号 URL。",
            evidence=[f"页面链接：{link_hits[0]} 等 {len(link_hits)} 个"])
    return make_check(26, DIM, "bad", "官方账号关联", 0, 3,
        "未检测到任何官方账号关联（sameAs 与页面链接均无）。",
        "在 Organization JSON-LD 的 sameAs 与页脚中关联官方社媒账号。",
        evidence=[f"{context.domain}：未发现官方账号关联"])


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def run(context):
    if context is None:
        return []
    pages = [p for p in (context.pages or []) if p is not None]
    checks = [
        _check22(context, pages),
        _check23(context, pages),
        _check24(context, pages),
        _check25(context, pages),
        _check26(context, pages),
    ]
    # 可选 AI 增强（DeepSeek）：为每项补充 ai_impact/ai_fix，并追加维度总评。
    # 未配置 key / 失败时静默降级为纯规则模式，分数不受影响。
    checks, summary = _ai.enhance(context.domain, "能被信任", checks)
    if summary:
        checks.append(make_check(903, DIM, "advice", "AI 维度总评", None, None,
                                 summary, "",
                                 evidence=[f"由 DeepSeek 生成（{context.domain}）"]))
    return checks
