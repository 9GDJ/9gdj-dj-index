# Panda DJ Index — GitHub 全自动运行部署（完整方案）

本包让整个站点**在 GitHub 上自动运行**：前端由 GitHub Pages 托管，后端由 Render 免费托管，
**每日 10:00 / 22:00 由 GitHub Actions 自动抓取 pandadj 新曲目、更新数据并推送**，全程无需你开电脑。

## 包内结构（一个仓库即可）

```
panda-dj-index/
├── .github/workflows/scrape.yml   # 定时抓取工作流（每天 10:00/22:00 自动跑）
├── scripts/                       # scrape/classify/clean_bad/build_site 四个脚本
├── data/                          # 全量数据（92,194 条）+ 断点状态，首次已含
├── site/                          # 前端静态站（GitHub Pages 指向此目录）
├── server.py                      # 后端代理（注册/登录/试听/下载）
├── render.yaml                    # Render 自动部署配置
├── requirements.txt
└── users.json
```

## 一、上线步骤（一次配置，永久自动）

### 1. 创建仓库并推送全部内容

1. 打开 github.com → New repository → 名称如 `panda-dj-index` → 选 Private（推荐）
2. 把本 zip 解压后的**全部内容**推上去（见文末"推送方式"）

### 2. 开启 GitHub Pages（前端）

仓库 Settings → **Pages** → Source 选 `Deploy from a branch` → 分支 `main` → 目录选 **`/site`** → Save
→ 约 1 分钟后访问 `https://<你的用户名>.github.io/panda-dj-index/`

### 3. 部署后端（Render，免费）

1. 登录 [render.com](https://render.com) → New → **Blueprint Instance** → 选择刚才的仓库
2. Render 自动读取 render.yaml 部署 `server.py`，几分钟后得到后端地址 `https://panda-index-backend.onrender.com`
3. 浏览器打开该地址 `/api/session`，返回 `{"ok": false}` 即后端已运行

### 4. 前端接上后端（关键一步）

1. 打开仓库里的 `site/index.html`（或本地解压目录里改好再推）
2. 把第一行改成：

   ```html
   <script>window.API_BASE = 'https://panda-index-backend.onrender.com';</script>
   ```

3. 推送后 Pages 自动更新，全站注册/登录/试听/下载即打通

### 5. 验证自动抓取

仓库 → **Actions** 页签，能看到 `daily-scrape-update` 工作流已按计划运行（下次 10:00/22:00）；
也可点 **Run workflow** 手动触发一次验证。每次运行会自动把新数据 commit 并 push，
Pages 随之自动更新——**这就是"自动运行"**。

## 二、自动运行原理

| 组件 | 角色 | 自动程度 |
|---|---|---|
| GitHub Actions | 每天 10:00/22:00 跑 抓取→分类→清洗→重建，自动 commit + push | 全自动 |
| GitHub Pages | 托管 `site/`，每次 push 自动重新发布 | 全自动 |
| Render | 持续运行 `server.py` 后端（注册/登录/代理播放/下载） | 持续在线 |
| 抓取断点 | `data/scrape_state.json` 记录已完成页，只抓新增 | 增量高效 |

## 三、注意事项

- **GitHub Actions 免费额度**：2000 分钟/月。日常每次只抓新增 1-2 页（约 2 分钟），每月约 60 次 ≈ 120 分钟，额度充足
- **Render 免费实例**：约 15 分钟无访问休眠，首次打开需等几秒唤醒
- **pandadj 风控**：对高频请求有限制，登录/试听偶发失败稍后重试即可
- **数据体积**：全量约 69MB，远低于 GitHub 仓库限制（单文件 100MB / 推荐 1GB）
- **私有仓库**：Pages 支持私有仓库（需登录 GitHub 访问）；对外公开则选 Public

## 四、推送方式（任选）

**方式 1：GitHub Desktop（推荐，图形界面）**
1. 安装 GitHub Desktop 并登录
2. File → New repository → 名称 `panda-dj-index` → 选好本地目录后把 zip 内容拷进去
3. 右上角 Publish repository → 选 Private/Public → 完成

**方式 2：git 命令行**

```bash
git init
git add -A
git commit -m "init"
git branch -M main
git remote add origin https://github.com/<你的用户名>/panda-dj-index.git
git push -u origin main
```

**方式 3：网页上传**（文件较多需分批，每个 ≤25MB）
仓库首页 → Add file → Upload files → 拖入 `site/`、`scripts/`、`data/` 等目录内容（注意 GitHub 网页上传不保留子目录结构，多个目录需逐批上传到对应路径）
