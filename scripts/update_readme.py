# -*- coding: utf-8 -*-
"""
Update README.md with live stats from data/stats.json.
Run after build_site.py (GitHub Actions + local).
Generates a GitHub-style Chinese README; data table is rebuilt on every run.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS = os.path.join(ROOT, "data", "stats.json")
README = os.path.join(ROOT, "README.md")

with open(STATS, encoding="utf-8") as f:
    s = json.load(f)

fmt = s.get("format", {})
lang = s.get("language", {})
combo = s.get("combo", {})

rows = [
    ("曲目总数", f"**{s.get('total', 0):,}**"),
    ("单曲", f"{fmt.get('single', 0):,}"),
    ("串烧", f"{fmt.get('mashup', 0):,}"),
    ("中文", f"{lang.get('zh', 0):,}"),
    ("英文", f"{lang.get('en', 0):,}"),
    ("其他", f"{lang.get('other', 0):,}"),
    ("中文单曲", f"{combo.get('zh_single', 0):,}"),
    ("英文单曲", f"{combo.get('en_single', 0):,}"),
    ("中文串烧", f"{combo.get('zh_mashup', 0):,}"),
    ("英文串烧", f"{combo.get('en_mashup', 0):,}"),
    ("入库日期范围", f"{s.get('earliest_date', '')} ~ {s.get('latest_date', '')}（{s.get('date_count', 0)} 天）"),
    ("今日新增", f"{s.get('today_count', 0)}（{s.get('today', '')}）"),
    ("串烧大小阈值", f"\u2265 {s.get('size_threshold_mib', 100.0):g} MiB"),
]
table = "\n".join(f"| {k} | {v} |" for k, v in rows)

readme = f"""<div style="background:linear-gradient(135deg,#FF2BD6 0%,#A855F7 55%,#6366F1 100%);border-radius:14px;padding:18px 22px;color:#ffffff;margin:0 0 14px;box-shadow:0 6px 20px rgba(255,43,214,.15)">

# 🎵 9GDJ DJ Index

**互联网公开曲目 · 元数据索引站** · 纯静态 GitHub Pages，支持搜索 / 日期归档 / 页内试听 / 一键下载

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-ffffff?style=flat&logo=github&logoColor=white&labelColor=222222)](https://9gdj.com/9gdj-dj-index/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Edge Proxy](https://img.shields.io/badge/Edge%20Proxy-Workers-F38020?style=flat&logo=cloudflare&logoColor=white)](https://workers.cloudflare.com/)
[![PWA](https://img.shields.io/badge/PWA-Enabled-5A0FC8?style=flat&logo=pwa&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)
[![Data](https://img.shields.io/badge/Data-每日自动更新-00C853?style=flat)]()
[![PRs](https://img.shields.io/badge/PRs-Welcome-ff69b4?style=flat)](https://github.com/9GDJ/9gdj-dj-index/pulls)

</div>

> 🧡 个人爱好项目 · 仅用于学习交流与技术实践 · 无任何商业用途
>
> 站内仅抓取和展示公开列表中的**元数据**（文件名、大小、入库时间、来源链接），**不下载、不存储、不转存任何音频文件**；「试听 / 下载」由边缘代理层按需实时转发（不缓存、不落盘）。

---

## 📚 目录

[关于](#-关于本项目) · [功能](#-功能特性) · [架构](#-架构) · [数据概览](#-数据概览) · [分类规则](#-分类规则) · [项目结构](#-项目结构) · [本地运行](#-本地运行) · [自动更新](#-自动更新github-actions) · [部署](#-部署) · [技术栈](#-技术栈) · [版权](#-版权声明与免责声明)

---

## 🧡 关于本项目

- **性质**：个人兴趣驱动的开源练习项目，由作者业余时间维护。
- **目的**：练习 Python 数据流水线、静态站点生成、边缘计算代理与前端交互开发。
- **数据**：全部曲目元数据来自**互联网公开列表**，本站不拥有、不存储任何音频内容。
- **态度**：欢迎 Star / Fork / Issue 交流；若相关权利人认为展示不妥，请联系作者移除对应条目。

## ✨ 功能特性

- 🚀 **品牌 Hero**：曲目总数 / 单曲 / 串烧 / 中文 / 英文 / 今日新增 六项统计 + 分类入口 + 最新入库
- ⚡ **秒开首屏**：最近 30 天轻量索引先渲染，全量按需加载并缓存至本地
- 🗂️ **分类浏览**：单曲 / 串烧 × 中文 / 英文组合筛选
- 🔍 **全文搜索**：文件名即时模糊匹配（大小写不敏感）
- 📅 **日期归档**：全部入库日期网格，点击查看当天曲目
- 🎧 **页内试听**：五彩波纹播放器（Canvas 动态波形 + 蒙层进度），同域代理实时转发
- ⬇️ **一键下载**：保留原始文件名 + ID3 品牌化（艺术家 / 唱片集 / 流派）
- 🔑 **免登录授权**：打开站点即自动获得权限，会话复用
- 📱 **移动端适配** + 📦 **PWA 可安装**

## 🏗️ 架构

```mermaid
flowchart TB
  A[📄 GitHub Pages 静态站] -->|同域 /api 路由| B[☁️ Cloudflare Workers 代理层]
  B -->|实时转发音频流| C[🎵 公开列表音频源]
  D[⚙️ GitHub Actions 每日流水线] -.->|自动抓取·分类·构建·部署| A
```

- **前端**：纯静态（HTML + CSS + 原生 JS，无框架无构建步骤），索引数据位于 `site/index.html` 与 `site/data/tracks.json`。
- **边缘代理层**：部署于 Cloudflare Workers 的轻量转发服务（同域路由，不暴露独立后端地址）——维护免登录授权会话池，访客打开站点即自动获得授权；实时转发音频流并注入 ID3 品牌标签；整站零跳转。
- **自动化**：GitHub Actions 每日两次自动执行完整流水线（抓取 → 分类 → 清洗 → 构建 → 推送），Pages 自动重新部署。

## 📊 数据概览

_数据生成时间：{s.get('generated_at', '')[:16]}_

**核心指标**：

| 🎵 曲目总数 | 🎧 单曲 | 🔥 串烧 | ✨ 今日新增 |
|---|---|---|---|
| **{s.get('total', 0):,}** | {fmt.get('single', 0):,} | {fmt.get('mashup', 0):,} | **{s.get('today_count', 0)}**（{s.get('today', '')}） |

<details>
<summary><b>📊 详细分类</b>（点击展开）</summary>

| 指标 | 数值 |
|---|---|
{table}

</details>

## 🧭 分类规则

### 单曲 / 串烧

**主规则：文件大小 ≥ 100 MiB → 串烧；否则 → 单曲。**

**辅助规则：** 文件名含以下关键词之一也归为串烧（不受大小限制）：

`串烧`、`mashup`、`mash up`、`mixset`、`megamix`、`连续串`、`大串烧`、`串烧版`、`连续播放`

阈值与关键词可在 `scripts/classify.py` 顶部调整。

### 中文 / 英文

- 文件名含中文字符（Unicode `\\u4e00-\\u9fff`）→ **中文**
- 否则含拉丁字母（A-Za-z）→ **英文**
- 两者均无 → **其他**

### 每日最新

按入库时间（YYYY-MM-DD）分组，首页展示最新入库，日期归档页可按天浏览。

## 📁 项目结构

```
├── .github/workflows/     # 每日流水线（抓取/分类/清洗/构建/部署）
├── scripts/
│   ├── scrape.py          # 抓取公开列表新增曲目（断点续爬）
│   ├── classify.py        # 分类：单曲/串烧 + 中文/英文 + 统计
│   ├── clean_bad.py       # 清洗空文件名/零大小脏数据，重算统计
│   ├── build_site.py      # 静态站点生成器（HTML/CSS/JS/数据/PWA/同域代理注入）
│   └── update_readme.py   # 刷新 README 数据概览（本脚本）
├── data/                  # 流水线数据（raw_tracks.csv / stats.json / 状态文件）
├── pwa-assets/            # PWA 清单、Service Worker 模板、图标
├── site/                  # 构建产物 → 部署到 GitHub Pages
│   ├── index.html
│   ├── assets/
│   ├── data/              # tracks.json / tracks-recent.json / 分片 / stats.json / dates.json
│   └── sw.js / manifest.webmanifest
└── README.md
```

> 边缘代理层（Cloudflare Workers）为独立部署服务，源码按需另行维护，不在本仓库公开。

## 🚀 本地运行

**1. 与 CI 相同的完整流水线**

```bash
python scripts/scrape.py       # 抓取新增曲目（断点续爬不重复）
python scripts/classify.py     # 分类（大小阈值 + 关键词 + 语言）
python scripts/clean_bad.py    # 清洗脏数据并重算统计
python scripts/build_site.py   # 重建站点（site/ 目录）
python scripts/update_readme.py  # 刷新 README 数据概览
```

**2. 本地预览**

```bash
cd site
python -m http.server 8000
# 浏览器打开 http://localhost:8000
```

> 本地预览时搜索 / 浏览 / 日期归档均可用；试听 / 下载需要边缘代理层，可直接访问线上站点体验完整功能。

## 🔄 自动更新（GitHub Actions）

内置 `daily-scrape-update` 工作流，**每日两次**自动执行（北京时间 10:00 / 22:00，另支持手动触发与代码推送触发）：

```
抓取新增 → 分类 → 清洗 → 重建站点 → 刷新 README → 推送 → Pages 自动部署
```

完全无人值守，也可在 Actions 页面手动触发 `Run workflow`。

## 🌐 部署

1. **GitHub Pages**：仓库 Settings → Pages → Source 选择 *Deploy from a branch* → `main`（`site/` 为部署内容目录）。
2. **边缘代理层**：部署为 Cloudflare Worker（含 KV 绑定，源码独立维护不公开）。前端经**同域 API 路由**请求代理（不暴露独立后端地址），本地构建自动使用空值走 localhost（本地模式不请求代理）。

## 🛠️ 技术栈

- 抓取 / 清洗 / 构建：Python 3 + requests + BeautifulSoup4 + lxml
- 前端：纯静态 HTML + CSS + 原生 JavaScript
- 边缘代理层：Cloudflare Workers（KV 会话存储）
- 托管：GitHub Pages + GitHub Actions

## ⚖️ 版权声明与免责声明

- **数据来源**：本站所有曲目元数据（文件名、大小、入库时间、来源链接）采集自**互联网公开列表**，仅作技术演示与个人学习之用。
- **内容权属**：曲目名称、音频内容的著作权归原作者 / 原权利人所有。本站不存储、不缓存、不转存任何音频文件，试听 / 下载均为按需实时转发。
- **非商业用途**：本项目为个人爱好项目，无商业行为，不以任何形式获利。
- **请支持正版**：建议前往官方渠道收听、下载正版内容。若您是相关权利人且认为本站展示不妥，请通过 Issue 或联系方式告知，我们将在核实后尽快移除对应条目。
- **使用风险**：本项目按现状提供，作者不对因使用本项目产生的任何直接或间接损失承担责任。

## 📄 License

MIT

---

> ⭐ 欢迎 Star 支持 · 由 [GitHub Actions](https://github.com/features/actions) 每日自动维护 · 数据概览实时刷新
> © 2026 9GDJ · 仅供学习交流 · 支持正版
"""

with open(README, "w", encoding="utf-8", newline="\n") as f:
    f.write(readme)

print(f"README updated: {s.get('total', 0):,} tracks, {s.get('date_count', 0)} days")
