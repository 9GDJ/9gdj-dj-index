# Panda DJ Index — 前端 GitHub Pages 部署方案

## 一、总体架构

```
pandadj.com ──(每日抓取 10:00/22:00)──> 本地 scripts/scrape.py
        │
        ▼
data/raw_tracks.json（原始数据，断点续爬）
        │
        ▼ scripts/classify.py（分类：≥100.0 MiB → 串烧；其余单曲；中/英/其他）
        ▼ scripts/clean_bad.py（清洗空文件名/无大小条目，重算统计）
        ▼ scripts/build_site.py（生成静态站点）
        ▼
site/（纯静态：index.html + assets/ + data/tracks.json + stats.json + dates.json）
        │
        ▼ 上传到 GitHub
        ▼
GitHub Pages ──> https://<user>.github.io/<repo>/
```

## 二、纯静态前端（方案 A — 推荐，零成本）

**原理**：站点是纯静态文件（HTML/CSS/JS + JSON 数据），GitHub Pages 直接托管。
注册/登录/试听/下载依赖后端代理（本地 server.py 或云后端），前端先以"未登录只读浏览"可用。

### 步骤

1. **创建仓库**（已创建：`9GDJ/panda-dj-index`，Public）
2. **上传整站文件**：`site/` 目录下所有文件（index.html、assets/、data/）
   - 单文件 <25MB，用 GitHub 网页 Upload files 逐个上传
   - 或 git push（推荐）：`git push origin main`
3. **启用 GitHub Pages**：仓库 Settings → Pages → Source 选 `GitHub Actions`（已有 workflow 自动构建）或 `Deploy from a branch` → main / root
4. **访问**：`https://9gdj.com/panda-dj-index/`

### 数据更新（每日）

本地执行（与定时任务一致）：
```powershell
cd panda-index-site
python scripts\scrape.py      # 抓取新增
python scripts\classify.py    # 分类（≥100MiB 串烧）
python scripts\clean_bad.py   # 清洗
python scripts\build_site.py  # 重建站点
```
然后将 `site/data/` 下 3 个文件（tracks.json / stats.json / dates.json）上传/推送仓库，
Pages 自动重新部署（已有 .github/workflows/scrape.yml 的 Actions 模式）。

## 三、仓库内自动运行（方案 B — Actions 每日自动抓取）

仓库已含 `.github/workflows/scrape.yml`：GitHub Actions 按 cron 每日 10:00/22:00（UTC 2:00/14:00）
在云端自动执行 抓取→分类→清洗→构建→提交，Pages 自动发布。**完全无人值守**。

## 四、后端代理（注册/登录/试听/下载）说明

- 纯静态 Pages **不含后端**；试听/下载需要代理转发 pandadj 的音频（需登录态）。
- 本地：`server.py` 提供一体化服务（http://localhost:8765），注册/登录/试听/下载全站内完成。
- 云端（可选，免费）：Replit / Vercel 部署 `server.js`（Node 代理），前端 `API_BASE` 指向其 URL。
- 若仅做元数据索引展示，前端无需后端即可浏览/搜索/分页。

## 五、文件清单（打包内容）

```
panda-dj-index/
├── site/                     # 静态站点（部署到 Pages 的根目录）
│   ├── index.html
│   ├── assets/style.css
│   ├── assets/app.js
│   └── data/
│       ├── tracks.json       # 全量曲目（91,050 条）
│       ├── stats.json        # 统计
│       └── dates.json        # 日期归档
├── scripts/                  # 数据管线（scrape/classify/clean/build/enrich）
├── data/                     # 本地数据全量（JSON+CSV）
├── .github/workflows/scrape.yml  # Actions 自动抓取
├── server.py                 # 本地一体化服务（可选）
└── README-DEPLOY.md          # 本方案文档
```

## 六、数据口径（2026-09-25 更新）

- 总数 91,050；单曲 89,475（中 75,945 / 英 13,511 / 其他 19）；串烧 1,575（中 1,568 / 英 7）
- 分类规则：**≥100.0 MiB → 串烧；否则单曲**（用户定稿，仅按大小）
- 语言：剥括号后含中文字符 → 中文；含拉丁字符 → 英文；否则其他
- 今日新增 28 条；日期范围 2024-09-20 ~ 2026-09-25
