# 9GDJ DJ 索引

纯静态 GitHub Pages 曲目**元数据索引站**（数据来源：互联网公开列表）。
按 **单曲/串烧**（≥100 MiB 或含串烧关键词判定）、**中文/英文**分类，支持搜索、日期归档、最新入库，页内**五彩波纹播放器**试听 + 一键下载，**免登录自动授权**。

> ⚠️ 本项目仅抓取和展示公开列表中的元数据（文件名、大小、入库时间、来源链接），不下载、不存储、不转存任何音频文件。试听/下载由后端按需实时转发官方音频流（不缓存、不落盘）。

## 站点地址

| 环境 | 地址 |
|---|---|
| 线上 | https://9gdj.com/9gdj-dj-index/ |
| 本地 | `python server.py` → http://localhost:8765 |

## 功能特性

- **免登录自动授权**：打开即可试听/下载。按访客 IP 从预置账号池稳定分配会话（同一 IP 始终同一账号、不同 IP 自动分散），无注册登录界面、整站不跳转源站。
- **分类浏览**：全部单曲 / 全部串烧 / 中文单曲 / 英文单曲 / 中文串烧 / 英文串烧。
- **搜索 + 日期归档**：按文件名搜索；日期归档 700+ 天。
- **详情页**：文件名 / 大小 / 入库时间 / 标签 + 五彩波纹播放器 + 美化下载按钮。
- **PWA**：手机浏览器可「添加到主屏幕」，独立窗口、秒开、离线可用。
- **移动端深度适配**：≤620px 列表卡片化、大触控按钮、iPhone 安全区。

## 自动更新（GitHub Actions）

`.github/workflows/scrape.yml` 每日 **北京时间 10:00 / 22:00** 自动执行：

```
抓取(pandadj公开列表) → 分类(单曲/串烧、中文/英文) → 清洗(空文件名/0大小) → 建站 → 部署 GitHub Pages
```

上传文件到 main 分支也会自动触发（内部提交带 `[skip ci]` 防死循环）。

## 后端（试听/下载代理）

- **本地**：`server.py`（Python，直连源站全速）。
- **线上**：Deno Deploy（https://ideal-tarantula-8406.9gdj.deno.net）。
- 前端自动切换 API 地址：`localhost` → 本地后端；线上 → Deno。
- 账号池按 IP 分配，试听失败自动换备选账号重试。

## 目录结构

```
├── .github/workflows/scrape.yml  # 每日自动更新
├── scripts/                      # scrape.py / classify.py / clean_bad.py / build_site.py / enrich_sources.py
├── site/                         # 生成的静态站点（部署产物）
│   ├── index.html / sw.js / manifest.webmanifest
│   ├── assets/                   # style.css / app.js / 波纹播放器 / PWA 图标
│   └── data/                     # tracks.json / stats.json / dates.json
├── data/                         # 分类结果 / 统计 / 抓取断点（中间数据）
├── pwa-assets/                   # PWA 资源（build 时复制进 site/）
├── server.py                     # 本地一体化服务（静态站点 + 后台代理）
└── requirements.txt
```

## 本地运行

```bash
pip install -r requirements.txt
python server.py        # http://localhost:8765
```

## 数据概览（截至 2026-09-25）

| 指标 | 数值 |
|---|---|
| 曲目总数 | 91,079 |
| 单曲 / 串烧 | 89,502 / 1,577 |
| 中文 / 英文 | 77,526 / 13,534 |
| 日期归档 | 702 天 |

## 免责声明

本站为个人学习用途的元数据索引，不提供任何音频文件的存储与分发；音频流由后端按需转发自公开来源，版权归原权利人所有。
