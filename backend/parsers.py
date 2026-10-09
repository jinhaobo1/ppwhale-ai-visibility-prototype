"""共享解析器：把原始 HTTP 响应解析成 context 里的数据结构。

合作者不需要碰这个文件；所有解析结果都通过 ScanContext 提供给模块。
"""

import json
import re
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup

from context import ParsedPage, RobotsInfo, SitemapInfo, LlmsInfo


def parse_home(domain: str, response) -> ParsedPage:
    """把首页 HTTP 响应解析成 ParsedPage。response 为 None 表示抓取失败。"""
    if response is None:
        return ParsedPage(url=f"https://{domain}/", status=None)
    html = response.text or ""
    return _parse_page_html(domain, str(response.url), response.status_code, html)


def _parse_page_html(domain: str, final_url: str, status: int, html: str) -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    meta_desc = ""
    m = soup.find("meta", attrs={"name": "description"})
    if m and m.get("content"):
        meta_desc = m["content"].strip()

    canonical = None
    c = soup.find("link", attrs={"rel": "canonical"})
    if c and c.get("href"):
        canonical = c["href"]

    og_url = None
    og = soup.find("meta", attrs={"property": "og:url"})
    if og and og.get("content"):
        og_url = og["content"]

    og_site_name = None
    osn = soup.find("meta", attrs={"property": "og:site_name"})
    if osn and osn.get("content"):
        og_site_name = osn["content"].strip()

    # robots 指令
    noindex = False
    nosnippet = False
    r = soup.find("meta", attrs={"name": "robots"})
    robots_content = (r.get("content") or "").lower() if r else ""
    if "noindex" in robots_content:
        noindex = True
    if "nosnippet" in robots_content or "max-snippet:0" in robots_content:
        nosnippet = True

    # JSON-LD 完整解析：数组/@graph 摊平成 dict 列表；逐段记录解析失败
    # ★ 必须在 decompose script 之前提取，否则 JSON-LD 会被删掉
    jsonld, jsonld_errors = _extract_jsonld(soup)

    # @type 列表（保留给维度 1/2 使用；从摊平后的 jsonld 派生，与旧口径一致）
    schemas = []
    for it in jsonld:
        if isinstance(it, dict) and it.get("@type"):
            schemas.append(it["@type"])

    author_elems = _count_author_signals(soup, jsonld)

    # 正文长度：去掉 script/style/noscript 后的可见文本
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text_len = len(soup.get_text(" ", strip=True))
    visible_text = soup.get_text(" ", strip=True)

    # 联系方式与站外链接（维度 4 使用）
    emails = _extract_emails(visible_text)
    phones = _extract_phones(visible_text)
    external_links = _extract_external_links(domain, soup)

    return ParsedPage(
        url=final_url,
        status=status,
        final_url=final_url,
        title=title,
        meta_desc=meta_desc,
        h1_count=len(soup.find_all("h1")),
        h2_count=len(soup.find_all("h2")),
        text_len=text_len,
        schemas=schemas,
        canonical=canonical,
        og_url=og_url,
        noindex=noindex,
        nosnippet=nosnippet,
        list_count=len(soup.find_all(["ul", "ol"])),
        table_count=len(soup.find_all("table")),
        internal_links=_count_internal_links(domain, soup),
        strong_count=len(soup.find_all(["strong", "em"])),
        time_elems=len(soup.find_all("time")),
        author_elems=author_elems,
        jsonld=jsonld,
        jsonld_errors=jsonld_errors,
        og_site_name=og_site_name,
        emails=emails,
        phones=phones,
        external_links=external_links,
    )


def _count_internal_links(domain: str, soup) -> int:
    """统计正文里指向本站的链接数（粗略：排除导航/页脚可能仍不精确，后续可优化）。"""
    count = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/") or domain in href:
            count += 1
    return count


def _count_author_signals(soup, jsonld: list | None = None) -> int:
    """统计作者署名信号（rel=author、class 含 author、JSON-LD 里的 author）。"""
    n = len(soup.find_all(attrs={"rel": "author"}))
    n += len(soup.find_all(attrs={"class": re.compile("author", re.I)}))
    for it in (jsonld or []):
        if isinstance(it, dict) and "author" in it:
            n += 1
    return n


def parse_robots(domain: str, response) -> RobotsInfo | None:
    """解析 robots.txt。"""
    if response is None or response.status_code != 200:
        return None
    text = response.text or ""
    allows_root = "Disallow: /" not in text
    return RobotsInfo(url=f"https://{domain}/robots.txt", status=200, text=text,
                      found=True, allows_root=allows_root)


def parse_sitemap(response) -> SitemapInfo:
    """解析 sitemap（支持普通 URL 集与 sitemap index）。"""
    info = SitemapInfo()
    if response is None or response.status_code != 200:
        return info
    info.found = True
    try:
        soup = BeautifulSoup(response.text, "xml")
        for loc in soup.find_all("loc"):
            u = loc.get_text(strip=True)
            if u and u not in info.urls:
                info.urls.append(u)
    except Exception:
        pass
    return info


def parse_llms(response) -> LlmsInfo:
    """解析 llms.txt。"""
    if response is None or response.status_code != 200:
        return LlmsInfo(found=False)
    return LlmsInfo(found=True, status=200)


# ---------------------------------------------------------------------------
# 以下为维度 3/4（understand/trust）扩充的解析辅助函数（只加不改）
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# 电话：数字 + 分隔符组成的 7-16 位号码（含 +86 等前缀），排除纯日期/年份
PHONE_RE = re.compile(r"\+?\d(?:[\d\s\-–—]{5,}\d)")
_EXTERNAL_SKIP_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
                           ".ico", ".css", ".js", ".pdf", ".zip", ".mp3",
                           ".mp4", ".woff", ".woff2")


def _flatten_jsonld(data, out: list):
    """把 JSON-LD 摊平成「无嵌套 @graph、无数组」的 dict 列表。"""
    if isinstance(data, list):
        for it in data:
            _flatten_jsonld(it, out)
    elif isinstance(data, dict):
        graph = data.get("@graph")
        if isinstance(graph, list):
            node = {k: v for k, v in data.items() if k != "@graph"}
            if node.get("@type") or node.get("@id"):
                out.append(node)
            for g in graph:
                _flatten_jsonld(g, out)
        else:
            out.append(data)


def _extract_jsonld(soup) -> tuple[list, int]:
    """解析页面全部 JSON-LD 块。返回 (摊平后的 dict 列表, 解析失败块数)。"""
    out: list = []
    errors = 0
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except Exception:
            errors += 1
            continue
        _flatten_jsonld(data, out)
    return out, errors


def _extract_emails(text: str) -> list[str]:
    """从可见文本提取邮箱（去重，上限 20）。"""
    found = []
    for m in EMAIL_RE.finditer(text):
        s = m.group().strip(".,;:，。；：")
        if s.lower() not in {x.lower() for x in found}:
            found.append(s)
        if len(found) >= 20:
            break
    return found


def _extract_phones(text: str) -> list[str]:
    """从可见文本提取电话号（去重，上限 20，排除纯日期/年份）。"""
    found = []
    for m in PHONE_RE.finditer(text):
        s = m.group().strip()
        digits = re.sub(r"\D", "", s)
        if not (7 <= len(digits) <= 16):
            continue
        if re.fullmatch(r"(19|20)\d{6,}", digits):   # 20260101 之类日期
            continue
        if s not in found:
            found.append(s)
        if len(found) >= 20:
            break
    return found


def _extract_external_links(domain: str, soup) -> list[str]:
    """提取页面里的站外链接（去重，上限 50）。"""
    found = []
    for a in soup.find_all("a", href=True):
        href = (a["href"] or "").strip()
        if not href.startswith(("http://", "https://")):
            continue
        try:
            host = urlparse(href).hostname or ""
        except Exception:
            continue
        if not host or domain in host:
            continue
        try:
            if urlparse(href).path.lower().endswith(_EXTERNAL_SKIP_SUFFIXES):
                continue
        except Exception:
            pass
        if href not in found:
            found.append(href)
        if len(found) >= 50:
            break
    return found
