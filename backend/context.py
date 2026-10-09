"""扫描上下文（契约层）。

框架负责「抓取 + 解析」，把结果整理成这些数据结构，交给模块。
模块只读这些结构，不自己抓取——这就是 5 个模块能并行开发、互不冲突的关键。
"""

from dataclasses import dataclass, field


@dataclass
class ParsedPage:
    """一个已抓取并解析好的代表页面（模块只读）。"""
    url: str
    status: int | None = None          # HTTP 状态码（None=抓取失败）
    final_url: str | None = None       # 重定向后的最终 URL
    title: str = ""
    meta_desc: str = ""
    h1_count: int = 0
    h2_count: int = 0
    text_len: int = 0                  # 去脚本后可见文本字符数
    schemas: list = field(default_factory=list)   # JSON-LD 的 @type 列表
    canonical: str | None = None
    og_url: str | None = None
    noindex: bool = False
    nosnippet: bool = False
    list_count: int = 0                # ul/ol 数量
    table_count: int = 0
    internal_links: int = 0            # 正文内站内链接数
    strong_count: int = 0              # strong/em 重点标记数
    time_elems: int = 0                # time 标签 / 日期信息数量
    author_elems: int = 0              # 作者署名信号数量
    # ↓ 以下为维度 3/4（understand/trust）扩充的只读数据（只加不改）
    jsonld: list = field(default_factory=list)    # 完整 JSON-LD 块（数组/@graph 已摊平为 dict 列表）
    jsonld_errors: int = 0             # JSON-LD 解析失败的块数
    og_site_name: str | None = None    # og:site_name
    emails: list = field(default_factory=list)    # 可见文本中的邮箱（去重）
    phones: list = field(default_factory=list)    # 可见文本中的电话（去重）
    external_links: list = field(default_factory=list)  # 页面里的站外链接（去重）


@dataclass
class RobotsInfo:
    """robots.txt 解析结果。"""
    url: str
    status: int | None = None
    text: str = ""
    found: bool = False
    allows_root: bool = True           # 是否允许抓取根路径


@dataclass
class SitemapInfo:
    """站点地图解析结果。"""
    found: bool = False
    urls: list = field(default_factory=list)   # 站内去重 URL 列表


@dataclass
class LlmsInfo:
    """llms.txt 解析结果。"""
    found: bool = False
    status: int | None = None


@dataclass
class ScanContext:
    """扫描上下文：框架产出的「所有模块共享的输入」。

    - home：首页解析结果
    - robots / sitemap / llms：关键文件解析结果
    - pages：所有代表页（含首页），供需要多页样本的检查项使用
    - discovered_urls：从 sitemap/首页链接发现的全部候选 URL（去重，含未被抓取的部分）
      → 维度 4 用来发现公司/联系/隐私等特定页面
    """
    domain: str
    home: ParsedPage | None = None
    robots: RobotsInfo | None = None
    sitemap: SitemapInfo = field(default_factory=SitemapInfo)
    llms: LlmsInfo = field(default_factory=LlmsInfo)
    pages: list = field(default_factory=list)   # list[ParsedPage]
    discovered_urls: list = field(default_factory=list)   # list[str]（只加不改）
