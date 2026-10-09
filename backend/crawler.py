"""共享抓取器：首页 + 关键文件 + 有限数量的代表页。

合作者不需要碰这个文件。它把抓取结果整理成 ScanContext 交给所有模块。

有界原则（防止爬全站失控）：
- 代表页数量有上限（MAX_REPRESENTATIVE_PAGES）
- 共享一个 AsyncClient、有限并发、逐请求超时
- 基础 SSRF 防护（拒绝 localhost / 内网地址）
"""

import asyncio
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup

from context import ScanContext, ParsedPage
from parsers import parse_home, parse_robots, parse_sitemap, parse_llms, _parse_page_html

USER_AGENT = "PPWhale-AI-Visibility-Checker/0.1 (+https://ppwhale.com)"
TIMEOUT = 15.0
MAX_REPRESENTATIVE_PAGES = 8   # 代表页上限
CONCURRENCY = 5                # 并发抓取上限

# 明显无关的文件扩展名（不抓）
SKIP_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
                 ".css", ".js", ".pdf", ".zip", ".mp3", ".mp4", ".woff", ".woff2")


def normalize(raw_url: str) -> str:
    """校验并规范化输入，返回纯域名。非法输入抛 ValueError。"""
    raw_url = (raw_url or "").strip()
    if not raw_url:
        raise ValueError("请输入官网地址，例如 example.com。")
    if not raw_url.startswith(("http://", "https://")):
        raw_url = "https://" + raw_url
    parsed = urlparse(raw_url)
    host = parsed.hostname or ""
    if not host or "." not in host:
        raise ValueError("请输入有效的官网域名，例如 example.com。")
    _guard_ssrf(host)
    return host


def _guard_ssrf(host: str):
    """基础 SSRF 防护：拒绝 localhost 与私网/保留地址。

    TODO: 生产环境应做 DNS 解析后再校验（防 DNS rebinding），此处先挡直接输入的私网地址。
    """
    host = host.lower()
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise ValueError("不允许检测本机或内网地址。")
    if host.startswith(("10.", "192.168.", "169.254.", "172.16.", "172.17.",
                        "172.18.", "172.19.", "172.20.", "172.21.", "172.22.",
                        "172.23.", "172.24.", "172.25.", "172.26.", "172.27.",
                        "172.28.", "172.29.", "172.30.", "172.31.")):
        raise ValueError("不允许检测内网地址。")


async def _get(client: httpx.AsyncClient, url: str):
    """抓取单个 URL，任何异常返回 None（不中断整体流程）。"""
    try:
        return await client.get(url)
    except Exception:
        return None


def _discover_page_urls(domain: str, home_html: str, sitemap_urls: list[str]) -> list[str]:
    """从 sitemap 和首页链接里发现候选代表页 URL（去重、过滤、设上限）。"""
    base = f"https://{domain}"
    candidates: list[str] = []

    # 来自 sitemap
    for u in sitemap_urls:
        if _is_scannable(domain, u):
            candidates.append(u)

    # 来自首页链接
    try:
        soup = BeautifulSoup(home_html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = urljoin(base, href)
            if _is_scannable(domain, href):
                candidates.append(href)
    except Exception:
        pass

    # 去重、去掉首页本身、设上限
    seen, result = set(), []
    home = base + "/"
    for u in candidates:
        if u.rstrip("/") == home.rstrip("/"):
            continue
        if u not in seen:
            seen.add(u)
            result.append(u)
        if len(result) >= MAX_REPRESENTATIVE_PAGES:
            break
    return result


def _is_scannable(domain: str, url: str) -> bool:
    """判断 URL 是否可扫描：站内 + 非静态资源 + 无查询参数（简化）。"""
    if not url or not url.startswith(("http://", "https://")):
        return False
    try:
        p = urlparse(url)
    except Exception:
        return False
    if not p.hostname or domain not in p.hostname:
        return False
    if p.path.lower().endswith(SKIP_SUFFIXES):
        return False
    return True


async def crawl(domain: str) -> ScanContext:
    """抓取首页 + 关键文件 + 有限代表页，产出 ScanContext。"""
    base = f"https://{domain}"
    async with httpx.AsyncClient(
        timeout=TIMEOUT, follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        home_resp = await _get(client, base + "/")
        robots_resp = await _get(client, base + "/robots.txt")
        sitemap_resp = await _get(client, base + "/sitemap.xml")
        llms_resp = await _get(client, base + "/llms.txt")

    # 解析关键文件
    home = parse_home(domain, home_resp)
    robots = parse_robots(domain, robots_resp)
    sitemap = parse_sitemap(sitemap_resp)
    llms = parse_llms(llms_resp)

    # 发现并抓取代表页
    page_urls = _discover_page_urls(domain, home_resp.text if home_resp else "", sitemap.urls)
    pages: list[ParsedPage] = [home] if home else []

    async def fetch_one(url: str) -> ParsedPage:
        async with httpx.AsyncClient(
            timeout=TIMEOUT, follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            r = await _get(client, url)
        if r is not None and r.status_code == 200:
            return _parse_page_html(domain, str(r.url), r.status_code, r.text)
        return ParsedPage(url=url, status=r.status_code if r else None)

    sem = asyncio.Semaphore(CONCURRENCY)

    async def limited(url):
        async with sem:
            return await fetch_one(url)

    results = await asyncio.gather(*(limited(u) for u in page_urls))
    pages.extend([p for p in results if p is not None])

    return ScanContext(
        domain=domain, home=home, robots=robots,
        sitemap=sitemap, llms=llms, pages=pages,
    )
