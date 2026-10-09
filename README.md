# ppwhale-ai-visibility-prototype

泡泡鲸科技（PPWhale）官网「AI 信源诊断 / 品牌可见性测试」模块的原型。

对任意官网做 AI 可见度诊断：五维评分（能被找到 / 看见 / 理解 / 信任 / 引用，共 100 分）+ 逐项检查证据与优化建议。

## 架构（模块化，5 人并行开发）

```
backend/
  main.py          # FastAPI 入口，POST /api/check
  engine.py        # 框架主循环：抓取上下文 → 调所有模块 → 汇总报告
  crawler.py       # 共享：抓取首页 + 关键文件 + 有限代表页
  parsers.py       # 共享：解析 HTML / JSON-LD / robots / sitemap
  context.py       # 契约：ScanContext / ParsedPage 等数据结构
  checks.py        # 契约：五维定义 + 30 项 ID 分配 + make_check
  modules/         # ★ 5 个维度模块，每人负责一个（只改自己的文件夹）
    find/          #   能被找到（10 分，ID 1-8）✅ 已实现
    see/           #   能被看见（30 分，ID 9-16）✅ 已实现
    understand/    #   能被理解（25 分，ID 17-21）✅ 已实现
    trust/         #   能被信任（15 分，ID 22-26）✅ 已实现
    cite/          #   能被引用（20 分，ID 27-30）⏳ 待实现
  tests/           # 单元测试（离线，不依赖外网）
docs/
  spec.md          # 30 项真检测规格（实现说明书）
```

**合作者请看 `backend/modules/README.md`**（模块开发指南）和 `docs/spec.md`（规格）。

## 快速开始（后端）

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

测试接口：

```bash
curl -X POST http://127.0.0.1:8000/api/check \
  -H "Content-Type: application/json" \
  -d '{"url":"ppwhale.com"}'
```

跑单元测试：

```bash
cd backend
.venv\Scripts\python tests\test_framework.py          # 框架层
.venv\Scripts\python tests\test_find_module.py        # 维度1 能被找到
.venv\Scripts\python tests\test_see_module.py         # 维度2 能被看见
.venv\Scripts\python tests\test_understand_module.py  # 维度3 能被理解
.venv\Scripts\python tests\test_trust_module.py       # 维度4 能被信任
.venv\Scripts\python tests\test_parsers_ext.py        # 解析器扩充字段
```

## 当前状态

- ✅ 框架 + 契约 + 模块注册表：已就绪，5 人可并行开发
- ✅ `find`（能被找到，10 分）、`see`（能被看见，30 分）：已实现
- ✅ `understand`（能被理解，25 分）、`trust`（能被信任，15 分）：已实现，
  含离线测试 `tests/test_understand_module.py`、`tests/test_trust_module.py`、
  `tests/test_parsers_ext.py`
- ⏳ `cite`（能被引用，20 分）：仍为空壳，待实现
- ⏳ 前端接入：把原型 HTML 的假动画替换成调 `/api/check`

## 技术栈

- 后端：Python + FastAPI + httpx + BeautifulSoup
- 前端：单文件 HTML（基于 PPWhale 官网原型的交互层）
