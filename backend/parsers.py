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

    # robots 指令
    noindex = False
    nosnippet = False
    r = soup.find("meta", attrs={"name": "robots"})
    robots_content = (r.get("content") or "").lower() if r else ""
    if "noindex" in robots_content:
        noindex = True
    if "nosnippet" in robots_content or "max-snippet:0" in robots_content:
        nosnippet = True

    # 正文长度：去掉 script/style/noscript 后的可见文本
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text_len = len(soup.get_text(" ", strip=True))

    # JSON-LD @type 列表
    schemas = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for it in items:
                if isinstance(it, dict) and it.get("@type"):
                    schemas.append(it["@type"])
        except Exception:
            pass

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
        author_elems=_count_author_signals(soup),
    )


def _count_internal_links(domain: str, soup) -> int:
    """统计正文里指向本站的链接数（粗略：排除导航/页脚可能仍不精确，后续可优化）。"""
    count = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/") or domain in href:
            count += 1
    return count


def _count_author_signals(soup) -> int:
    """统计作者署名信号（rel=author、class 含 author、JSON-LD 里的 author）。"""
    n = len(soup.find_all(attrs={"rel": "author"}))
    n += len(soup.find_all(attrs={"class": re.compile("author", re.I)}))
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for it in items:
                if isinstance(it, dict) and "author" in it:
                    n += 1
        except Exception:
            pass
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
