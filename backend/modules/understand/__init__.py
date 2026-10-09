"""模块3：能被理解（25 分）——品牌、网站与页面结构化标记。

检查项（ID 17-21，见 docs/spec.md）：
  17 品牌实体标记      5 分  Organization/Brand 及名称/URL/logo/联系方式
  18 网站主体标记      4 分  WebSite 及名称/URL/搜索入口（含 @graph 解析）
  19 面包屑标记        4 分  BreadcrumbList 层级/名称/URL 校验
  20 代表页面专项标记  8 分  文章/产品/FAQ 页对应 BlogPosting/Product/FAQPage
  21 结构化数据有效性  4 分  逐段解析 JSON-LD（数组/@graph），统计解析失败

规则：
  - 入口 run(context) -> list[dict]，只读 context，不自己抓取；
  - 评分用离散判定规则，抓取顺序不影响结果；
  - 每个检查项始终返回，检测不到如实报 bad/warn。
"""

import json
from urllib.parse import urlparse

from checks import make_check

DIM = 2  # 维度下标（能被理解）

BRAND_TYPES = {"Organization", "Brand"}
WEBSITE_TYPES = {"WebSite"}
BREADCRUMB_TYPES = {"BreadcrumbList"}
ARTICLE_TYPES = {"BlogPosting", "Article", "NewsArticle", "TechArticle", "Report"}
PRODUCT_TYPES = {"Product", "Service"}
FAQ_TYPES = {"FAQPage"}

ARTICLE_URL_KW = ["/blog", "/news", "/article", "/post", "/insight", "/story",
                  "/wiki", "博客", "新闻", "资讯", "文章", "动态"]
PRODUCT_URL_KW = ["/product", "/goods", "/item", "/sku", "/service", "产品", "商品"]
FAQ_URL_KW = ["/faq", "/help", "/support", "/q&a", "常见问题", "帮助", "问答"]


# ---------------------------------------------------------------------------
# 通用辅助
# ---------------------------------------------------------------------------

def _type_set(node) -> set[str]:
    """取节点的 @type 集合（兼容字符串与列表）。"""
    t = node.get("@type") if isinstance(node, dict) else None
    if isinstance(t, str):
        return {t}
    if isinstance(t, list):
        return {x for x in t if isinstance(x, str)}
    return set()


def _get(node, *keys):
    """取第一个非空值；列表取首元素；dict 值尝试取 url/@id/contentUrl。"""
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


def _of_type(jsonld, types: set) -> list:
    return [n for n in jsonld if _type_set(n) & types]


def _url_host(url) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# ID 17 品牌实体标记（5 分）
# ---------------------------------------------------------------------------

def _brand_contact(node) -> bool:
    """品牌实体是否带联系方式：contactPoint(telephone/email) / telephone / email / address。"""
    cp = node.get("contactPoint")
    if isinstance(cp, dict):
        cp = [cp]
    if isinstance(cp, list):
        for c in cp:
            if isinstance(c, dict) and (_get(c, "telephone") or _get(c, "email")):
                return True
    if node.get("telephone") or node.get("email") or node.get("address"):
        return True
    return False


def _check17(context):
    nodes = [n for p in context.pages for n in _of_type(p.jsonld, BRAND_TYPES)]
    if not nodes:
        return make_check(17, DIM, "bad", "品牌实体标记", 0, 5,
            "全站未检测到 Organization / Brand 结构化标记，AI 无法建立品牌实体档案。",
            "在首页等核心页面添加 JSON-LD Organization/Brand，并填写名称、官网、logo 与联系方式。",
            evidence=[f"{context.domain}：未发现品牌实体标记"])

    node = nodes[0]
    name = str(_get(node, "name") or "").strip()
    url = _get(node, "url", "@id") or ""
    logo = _get(node, "logo")
    contact = _brand_contact(node)
    fields = {
        "名称": bool(name),
        "官网URL": bool(url and context.domain in _url_host(url)),
        "logo": bool(logo),
        "联系方式": contact,
    }
    got = [k for k, v in fields.items() if v]
    missing = [k for k, v in fields.items() if not v]
    score = 1 + len(got)                     # 实体本身 1 分 + 每个字段 1 分
    status = "good" if score == 5 else ("warn" if score >= 3 else "bad")
    impact = f"检测到品牌实体标记，已含 {len(got)}/4 项关键字段"
    if missing:
        impact += f"（缺：{'、'.join(missing)}）"
    fix = ("保持现状。" if score == 5 else
           f"补齐缺失字段：{'、'.join(missing)}。"
           "name 用公司全称、url 与域名一致、logo 用 ImageObject/URL、"
           "联系方式用 contactPoint/telephone/email/address。")
    return make_check(17, DIM, status, "品牌实体标记", score, 5, impact, fix,
        evidence=[f"品牌实体：name={name or '(空)'}，url={url or '(空)'}，"
                  f"logo={'有' if logo else '无'}，联系方式={'有' if contact else '无'}"])


# ---------------------------------------------------------------------------
# ID 18 网站主体标记（4 分）
# ---------------------------------------------------------------------------

def _has_search_action(node) -> bool:
    """WebSite 标记是否带搜索入口（SearchAction 或含占位符的 target）。"""
    pa = node.get("potentialAction")
    if isinstance(pa, dict):
        pa = [pa]
    if not isinstance(pa, list):
        return False
    for a in pa:
        if not isinstance(a, dict):
            continue
        if "SearchAction" in _type_set(a):
            return True
        if "{" in json.dumps(a, ensure_ascii=False):
            return True
    return False


def _check18(context):
    nodes = [n for p in context.pages for n in _of_type(p.jsonld, WEBSITE_TYPES)]
    if not nodes:
        return make_check(18, DIM, "bad", "网站主体标记", 0, 4,
            "全站未检测到 WebSite 结构化标记（含 @graph 内），AI 难以识别网站主体与站内搜索。",
            "添加 JSON-LD WebSite 标记（可放入 @graph），填写 name、url 与 potentialAction 搜索入口。",
            evidence=[f"{context.domain}：未发现 WebSite 标记（已解析 @graph）"])
    node = nodes[0]
    name = str(_get(node, "name") or "").strip()
    url = _get(node, "url", "@id") or ""
    search = _has_search_action(node)
    if not name:
        score, status = 1, "bad"
        impact = "有 WebSite 标记但缺少名称，标记无效"
    elif not url:
        score, status = 2, "warn"
        impact = "WebSite 标记有名称但缺官网 URL"
    elif not search:
        score, status = 3, "warn"
        impact = "WebSite 名称与 URL 齐全，但缺站内搜索入口（SearchAction）"
    else:
        score, status = 4, "good"
        impact = "WebSite 标记齐全：名称 + URL + 站内搜索入口"
    fix = ("保持现状。" if score == 4 else
           "补齐 WebSite 的 name、url，并添加 potentialAction: SearchAction"
           "（target 含 {search_term_string}）。")
    return make_check(18, DIM, status, "网站主体标记", score, 4, impact, fix,
        evidence=[f"WebSite：name={name or '(空)'}，url={url or '(空)'}，"
                  f"搜索入口={'有' if search else '无'}"])


# ---------------------------------------------------------------------------
# ID 19 面包屑标记（4 分）
# ---------------------------------------------------------------------------

def _crumb_items(node) -> list:
    items = node.get("itemListElement")
    if isinstance(items, dict):
        items = [items]
    return items if isinstance(items, list) else []


def _crumb_ok(node, domain) -> bool:
    """面包屑有效：≥2 项，每项有名称+URL（同域），且 URL 层级逐级加深。"""
    items = _crumb_items(node)
    if len(items) < 2:
        return False
    prev = None
    for it in items:
        if not isinstance(it, dict):
            return False
        name = _get(it, "name")
        url = _get(it, "item", "@id", "url")
        if not name or not url:
            return False
        try:
            host = urlparse(url).hostname or ""
            path = urlparse(url).path.rstrip("/")
        except Exception:
            return False
        if domain not in host:
            return False
        if prev and not path.startswith(prev + "/"):
            return False
        prev = path
    return True


def _check19(context):
    total, valid = 0, 0
    evidence = []
    for p in context.pages:
        for node in _of_type(p.jsonld, BREADCRUMB_TYPES):
            total += 1
            ok = _crumb_ok(node, context.domain)
            if ok:
                valid += 1
            evidence.append(f"{p.url}：面包屑 {'有效' if ok else '无效'}"
                            f"（{len(_crumb_items(node))} 项）")
    if total == 0:
        return make_check(19, DIM, "bad", "面包屑标记", 0, 4,
            "全站未检测到 BreadcrumbList 标记，AI 难以理解页面层级关系。",
            "在内容页/详情页添加 BreadcrumbList，逐级列出名称与 URL。",
            evidence=[f"{context.domain}：未发现面包屑标记"])
    if valid == 0:
        return make_check(19, DIM, "bad", "面包屑标记", 1, 4,
            f"发现 {total} 条面包屑标记，但均不完整（缺名称/URL 或层级不合理）。",
            "每项 itemListElement 必须含 name 与 item URL，且 URL 逐级加深。",
            evidence=evidence)
    if valid == 1:
        return make_check(19, DIM, "warn", "面包屑标记", 2, 4,
            f"{total} 条面包屑中仅 1 条有效。",
            "为更多层级页补齐 BreadcrumbList。", evidence=evidence)
    if valid < total:
        return make_check(19, DIM, "warn", "面包屑标记", 3, 4,
            f"{valid}/{total} 条面包屑有效，其余缺字段或层级不合理。",
            "检查无效面包屑的名称与 URL 完整性、层级顺序。", evidence=evidence)
    return make_check(19, DIM, "good", "面包屑标记", 4, 4,
        f"{valid} 条面包屑全部有效（名称+URL 齐全、层级合理）。",
        "保持现状，新增层级页时同步添加 BreadcrumbList。", evidence=evidence)


# ---------------------------------------------------------------------------
# ID 20 代表页面专项标记（8 分）
# ---------------------------------------------------------------------------

def _page_types(page) -> tuple[set, set]:
    """判定页面类型（article/product/faq）与页面已有的 JSON-LD 类型。"""
    types, jt = set(), set()
    for n in page.jsonld:
        jt |= _type_set(n)
    if jt & ARTICLE_TYPES:
        types.add("article")
    if jt & PRODUCT_TYPES:
        types.add("product")
    if jt & FAQ_TYPES:
        types.add("faq")
    url_l = (page.url or "").lower()
    title_l = (page.title or "").lower()
    if any(k in url_l for k in ARTICLE_URL_KW):
        types.add("article")
    if any(k in url_l for k in PRODUCT_URL_KW):
        types.add("product")
    if any(k in url_l or k in title_l for k in FAQ_URL_KW):
        types.add("faq")
    if page.time_elems > 0 and page.author_elems > 0:
        types.add("article")
    return types, jt


def _check20(context):
    typed, matched = 0, 0
    detail = []
    for p in context.pages:
        types, jt = _page_types(p)
        if not types:
            continue
        typed += 1
        ok = (("article" in types and jt & ARTICLE_TYPES)
              or ("product" in types and jt & PRODUCT_TYPES)
              or ("faq" in types and jt & FAQ_TYPES))
        if ok:
            matched += 1
        detail.append(f"{p.url}：类型={'+'.join(sorted(types))}，"
                      f"专项标记={'有' if ok else '缺'}")
    if typed == 0:
        return make_check(20, DIM, "warn", "代表页面专项标记", 0, 8,
            "未检测到文章/产品/FAQ 类型页面，无法验证专项标记。",
            "若网站存在博客、产品、常见问题等内容，请确保可被抓取并添加对应 BlogPosting/Product/FAQPage 标记。",
            evidence=[f"{context.domain}：未发现文章/产品/FAQ 类型页面"])
    if matched == typed:
        return make_check(20, DIM, "good", "代表页面专项标记", 8, 8,
            f"{matched}/{typed} 个类型页面均有对应专项标记（BlogPosting/Product/FAQPage）。",
            "保持现状。", evidence=detail)
    if matched * 2 >= typed:
        return make_check(20, DIM, "warn", "代表页面专项标记", 5, 8,
            f"{matched}/{typed} 个类型页面有对应专项标记，其余缺失。",
            "为缺标记的文章/产品/FAQ 页补充对应 BlogPosting/Product/FAQPage。",
            evidence=detail)
    if matched > 0:
        return make_check(20, DIM, "bad", "代表页面专项标记", 2, 8,
            f"仅 {matched}/{typed} 个类型页面有专项标记。",
            "系统性地为文章/产品/FAQ 页补充结构化标记。", evidence=detail)
    return make_check(20, DIM, "bad", "代表页面专项标记", 0, 8,
        f"{typed} 个文章/产品/FAQ 页面均无专项标记。",
        "为文章页加 BlogPosting、产品页加 Product、FAQ 页加 FAQPage。",
        evidence=detail)


# ---------------------------------------------------------------------------
# ID 21 结构化数据有效性（4 分）
# ---------------------------------------------------------------------------

def _check21(context):
    blocks = sum(len(p.jsonld) for p in context.pages)
    errors = sum(p.jsonld_errors for p in context.pages)
    total = blocks + errors
    if total == 0:
        return make_check(21, DIM, "bad", "结构化数据有效性", 0, 4,
            "全站未检测到任何 JSON-LD 结构化数据。",
            "在首页添加品牌/网站 JSON-LD 标记，内容页添加对应专项标记。",
            evidence=[f"{context.domain}：JSON-LD 块数 0"])
    if errors == 0:
        return make_check(21, DIM, "good", "结构化数据有效性", 4, 4,
            f"{blocks} 段 JSON-LD 全部解析成功（含数组/@graph）。",
            "保持现状，新增标记时用 Google 富媒体测试工具校验。",
            evidence=[f"解析成功 {blocks} 段，失败 0 段"])
    if errors * 4 <= total:      # 失败率 ≤ 25%
        return make_check(21, DIM, "warn", "结构化数据有效性", 2, 4,
            f"{errors}/{total} 段 JSON-LD 解析失败（失败率 {errors * 100 // total}%）。",
            "检查失败片段：括号/引号/逗号是否配对、@type 是否合法。",
            evidence=[f"解析成功 {blocks} 段，失败 {errors} 段"])
    return make_check(21, DIM, "bad", "结构化数据有效性", 0, 4,
        f"{errors}/{total} 段 JSON-LD 解析失败，失败率过高。",
        "优先修复 JSON-LD 语法错误，AI 只能读取解析成功的标记。",
        evidence=[f"解析成功 {blocks} 段，失败 {errors} 段"])


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def run(context):
    if context is None:
        return []
    return [
        _check17(context),
        _check18(context),
        _check19(context),
        _check20(context),
        _check21(context),
    ]
