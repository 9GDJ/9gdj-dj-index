# 9GDJ DJ Index

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-222222?logo=github&logoColor=white)](https://9gdj.com/9gdj-dj-index/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Deno](https://img.shields.io/badge/Edge%20Proxy-Deno-000000?logo=deno&logoColor=white)](https://deno.com/)
[![PWA](https://img.shields.io/badge/PWA-Enabled-5A0FC8?logo=pwa&logoColor=white)](https://developer.mozilla.org/zh-CN/docs/Web/Progressive_web_apps)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

纯静态 [GitHub Pages](https://pages.github.com/) 站点：索引**互联网公开列表**中的舞曲曲目元数据，按**单曲 / 串烧**、**中文 / 英文**分类，支持搜索、日期归档、页内试听与一键下载。

> 本项目仅抓取和展示公开列表中的**元数据**（文件名、大小、入库时间、来源链接），**不下载、不存储、不转存任何音频文件**。站内「试听 / 下载」由边缘代理层按需实时转发音频流（不缓存、不落盘），访问者**免登录**自动获得试听 / 下载权限。

## 功能特性

- **首页**：统计卡片 + 分类入口 + 最新入库 30 首
- **分类浏览**：单曲 / 串烧 × 中文 / 英文组合筛选
- **全部曲目**：客户端分页（每页 50 首），格式 / 语言下拉筛选
- **搜索**：基于文件名的即时模糊搜索（大小写不敏感）
- **日期归档**：700+ 个入库日期网格，点击查看当天全部曲目
- **页内试听**：不跳转，科技风**波纹播放器**（Canvas 动态波形 + 播放/暂停 + 点击波形跳转进度），播放源由边缘代理层实时转发
- **一键下载**：下载 MP3，文件名保持原始文件名
- **下载文件 ID3 品牌化**：艺术家 / 唱片集 / 流派替换为 9GDJ.com 品牌信息（唱片集 = `9GDJ.com`），**标题保留原文件原有值不做替换**
- **移动端适配**：卡片化布局、整卡点击、首屏懒加载、滚动位置记忆
- **PWA**：可安装；Service Worker 缓存静态资源（缓存名随构建自动版本化）

## 架构

```
┌─────────────────┐      ┌────────────────────┐      ┌──────────────────┐
│   GitHub Pages   │      │   边缘代理层         │      │   公开列表 / 音频流 │
│   静态站 + 索引数据 │ ───▶ │  （Deno Deploy）   │ ───▶ │                  │
│   index/tracks   │      │   会话池 · 实时转发   │      │   来源站           │
└─────────────────┘      └────────────────────┘      └──────────────────┘
```

- **前端**：纯静态（HTML + CSS + 原生 JS，无框架无构建步骤），索引数据位于 `index.html` 与 `tracks.json`。
- **边缘代理层**：部署在边缘运行时（Deno Deploy）的轻量转发服务——维护免登录会话池，按访客指纹自动分配授权，实时转发音频流；无注册 / 登录界面，整站零跳转。
- **自动化**：GitHub Actions 每日自动执行完整流水线（抓取 → 分类 → 清洗 → 构建 → 推送），Pages 自动重新部署。

## 数据概览

_数据生成时间：2026-09-26T09:59_

| 指标 | 数值 |
|---|---|
| 曲目总数 | **91,110** |
| 单曲 | 89,529 |
| 串烧 | 1,581 |
| 中文 | 77,556 |
| 英文 | 13,535 |
| 其他 | 19 |
| 中文单曲 | 75,982 |
| 英文单曲 | 13,528 |
| 中文串烧 | 1,574 |
| 英文串烧 | 7 |
| 入库日期范围 | 2024-09-20 ~ 2026-09-26（703 天） |
| 今日新增 | 26（2026-09-26） |
| 串烧大小阈值 | ≥ 100 MiB |

## 分类规则

### 单曲 / 串烧

**主规则：文件大小 ≥ 100 MiB → 串烧；否则 → 单曲。**

**辅助规则：** 文件名含以下关键词之一也归为串烧（不受大小限制）：

`串烧`、`mashup`、`mash up`、`mixset`、`megamix`、`连续串`、`大串烧`、`串烧版`、`连续播放`

阈值与关键词可在 `scripts/classify.py` 顶部调整。

### 中文 / 英文

- 文件名含中文字符（Unicode `\u4e00-\u9fff`）→ **中文**
- 否则含拉丁字母（A-Za-z）→ **英文**
- 两者均无 → **其他**

### 每日最新

按入库时间（YYYY-MM-DD）分组，首页展示最新入库，日期归档页可按天浏览。

## 项目结构

```
├── .github/workflows/     # 每日流水线（抓取/分类/清洗/构建/部署）
├── scripts/
│   ├── scrape.py          # 抓取公开列表新增曲目（断点续爬）
│   ├── classify.py        # 分类：单曲/串烧 + 中文/英文 + 统计
│   ├── clean_bad.py       # 清洗空文件名/零大小脏数据，重算统计
│   ├── build_site.py      # 静态站点生成器（HTML/CSS/JS/数据/PWA）
│   └── update_readme.py   # 刷新 README 数据概览（本脚本）
├── deno-server/           # 边缘代理层源码（会话池、音频流转发、ID3 品牌标签）
├── pwa-assets/            # PWA 清单、Service Worker 模板、图标
├── site/                  # 构建产物 → 部署到 GitHub Pages
│   ├── index.html
│   ├── assets/
│   ├── data/              # tracks.json / stats.json / dates.json
│   └── sw.js / manifest.webmanifest
└── README.md
```

## 本地运行

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

> 本地预览时搜索 / 浏览 / 日期归档均可用；试听 / 下载需要边缘代理层（本地未部署代理时可用线上站点体验完整功能）。

## 自动更新（GitHub Actions）

内置 `daily-scrape-update` 工作流，**每日两次**自动执行（北京时间 10:00 / 22:00，另支持手动触发）：

```
抓取新增 → 分类 → 清洗 → 重建站点 → 刷新 README → 推送 → Pages 自动部署
```

完全无人值守，也可在 Actions 页面手动触发 `Run workflow`。

## 部署

1. **GitHub Pages**：仓库 Settings → Pages → Source 选择 *Deploy from a branch* → `main`（站点内容位于仓库根，或按实际目录配置）。
2. **边缘代理层**：将 `deno-server/` 部署到边缘运行时（Deno Deploy），并把前端 `API_BASE` 指向代理域名（构建时由 `build_site.py` 写入；本地构建自动使用空值走 localhost）。

## 技术栈

- 抓取 / 清洗 / 构建：Python 3 + requests + BeautifulSoup4 + lxml
- 前端：纯静态 HTML + CSS + 原生 JavaScript
- 边缘代理层：Deno
- 托管：GitHub Pages + GitHub Actions

## License

MIT
