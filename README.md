# ppwhale-ai-visibility-prototype

泡泡鲸科技（PPWhale）官网「AI 信源诊断 / 品牌可见性测试」模块的原型。

对任意官网做 AI 可见度诊断：五维评分（能被找到 / 看见 / 理解 / 信任 / 引用，共 100 分）+ 逐项检查证据与优化建议。

## 项目结构

```
backend/
  main.py          # FastAPI 入口，POST /api/check
  analyzer.py      # 抓取 → 解析 → 打分 → 汇总
  checks.py        # 五维框架定义
  requirements.txt # Python 依赖
index.html         # 前端原型（待接入后端）
```

## 快速开始（后端）

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

测试接口：

```bash
curl -X POST http://127.0.0.1:8000/api/check \
  -H "Content-Type: application/json" \
  -d '{"url":"ppwhale.com"}'
```

## 当前状态

- ✅ 后端骨架：能真实抓取首页 + robots.txt + sitemap.xml + llms.txt，并完成 8 项基础检测
- ⏳ 前端接入：待把原型里的假动画替换成调用 `/api/check`
- ⏳ 多页爬取：面包屑、文章署名、案例页等需多页分析的检查项待补充

## 技术栈

- 后端：Python + FastAPI + httpx + BeautifulSoup
- 前端：单文件 HTML（基于 PPWhale 官网原型的交互层）
