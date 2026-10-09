"""扫描上下文（契约层）。

框架负责「抓取 + 解析」，把结果整理成这些数据结构，交给模块。
模块只读这些结构，不自己抓取——这就是 5 个模块能并行开发、互不冲突的关键。

除汇总统计字段外，ParsedPage 还保留 raw_html（原始 HTML）与 jsonld_blocks
（完整 JSON-LD 对象），供需要更细粒度的模块自行解析，从而无需再改框架层。
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
    p_count: int = 0                   # 有实质文本的 <p> 段落数
    dl_count: int = 0                  # 定义列表 <dl> 数量
    question_headings: int = 0         # 疑问式标题（h1-h6）数量
    visible_date: bool = False         # 可见文本是否出现日期
    jsonld_dates: list = field(default_factory=list)  # JSON-LD 日期（datePublished/dateModified/dateCreated）
    raw_html: str = ""                 # 原始 HTML（供模块自行解析正文/标题/联系方式等）
    jsonld_blocks: list = field(default_factory=list)  # 每个 ld+json 脚本解析后的完整原始对象（含 @graph/数组）
    jsonld_errors: int = 0             # 解析失败的 ld+json 脚本块数


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
    """
    domain: str
    home: ParsedPage | None = None
    robots: RobotsInfo | None = None
    sitemap: SitemapInfo = field(default_factory=SitemapInfo)
    llms: LlmsInfo = field(default_factory=LlmsInfo)
    pages: list = field(default_factory=list)   # list[ParsedPage]
