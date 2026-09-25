#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态站点生成器：读取分类后的数据，生成纯静态 GitHub Pages 站点。

生成内容:
  site/index.html        — 主页面（含内嵌最新曲目，客户端路由）
  site/assets/style.css  — 样式表
  site/assets/app.js     — 客户端逻辑（分页/搜索/分类/日期归档）
  site/data/tracks.json  — 全量曲目（精简字段，供客户端加载）
  site/data/stats.json   — 统计数字
  site/data/dates.json   — 日期归档列表
"""

import html
import json
import os
import shutil
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
SITE_DIR = os.path.join(PROJECT_DIR, "site")

CLASSIFIED_JSON = os.path.join(DATA_DIR, "classified.json")
AUDIO_MAP_JSON = os.path.join(DATA_DIR, "audio_map.json")
STATS_JSON = os.path.join(DATA_DIR, "stats.json")

PAGE_SIZE = 50
LATEST_ON_HOME = 30


def load_data():
    with open(CLASSIFIED_JSON, "r", encoding="utf-8") as f:
        tracks = json.load(f)
    with open(STATS_JSON, "r", encoding="utf-8") as f:
        stats = json.load(f)
    # 合并来源音频直连地址（enrich_sources.py 独立产出的 audio_map.json，scrape/classify 不会清空）
    try:
        with open(AUDIO_MAP_JSON, "r", encoding="utf-8") as f:
            au_map = json.load(f)
        for t in tracks:
            t["audio_url"] = au_map.get(str(t["id"]), "")
        print(f"  合并音频直连地址: {len(au_map)} 条")
    except Exception as e:
        print(f"  警告: 未合并音频直连地址 ({e})")
    return tracks, stats


def build_minimal_tracks(tracks):
    """精简字段以减小 JSON 体积。"""
    out = []
    for t in tracks:
        out.append({
            "i": t["id"],
            "n": t["filename"],
            "s": t.get("size_mib"),
            "t": t.get("time", ""),
            "f": 0 if t.get("format") == "single" else 1,
            "l": {"zh": 0, "en": 1, "other": 2}.get(t.get("language"), 2),
            "d": t.get("date") or "",
            "u": t.get("source_url") or "",
            "au": t.get("audio_url") or "",
        })
    return out


def build_dates_list(tracks):
    """构建日期归档列表（日期 -> 数量），按日期倒序。"""
    date_count = defaultdict(int)
    for t in tracks:
        d = t.get("date")
        if d:
            date_count[d] += 1
    return sorted(date_count.items(), key=lambda x: x[0], reverse=True)


def generate_css():
    return """/* ===== 9GDJ DJ 索引 — 深色简洁音乐站风格 ===== */
:root {
  --bg: #0f1115;
  --bg-card: #181b21;
  --bg-hover: #1f232b;
  --border: #2a2e37;
  --text: #e4e6eb;
  --text-dim: #9ca3af;
  --text-faint: #6b7280;
  --accent: #10b981;
  --accent-hover: #059669;
  --accent-soft: rgba(16, 185, 129, 0.12);
  --warn: #f59e0b;
  --danger: #ef4444;
  --info: #3b82f6;
  --radius: 10px;
  --shadow: 0 2px 12px rgba(0,0,0,0.3);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Header ── */
header {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(8px);
}
.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 14px 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.logo {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--accent);
  white-space: nowrap;
}
.logo span { color: var(--text-dim); font-weight: 400; font-size: 0.85rem; }
nav { display: flex; gap: 6px; flex-wrap: wrap; }
nav a {
  padding: 6px 14px;
  border-radius: 6px;
  color: var(--text-dim);
  font-size: 0.9rem;
  transition: all 0.15s;
}
nav a:hover, nav a.active {
  background: var(--accent-soft);
  color: var(--accent);
  text-decoration: none;
}
.auth-entry {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 0.9rem;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}
.auth-entry:hover {
  background: var(--accent-soft);
  color: var(--accent);
}

.search-box {
  margin-left: auto;
  display: flex;
  gap: 8px;
  flex: 1;
  max-width: 360px;
  min-width: 200px;
}
.search-box input {
  flex: 1;
  padding: 8px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.15s;
}
.search-box input:focus { border-color: var(--accent); }
.search-box button {
  padding: 8px 18px;
  border: none;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.15s;
}
.search-box button:hover { background: var(--accent-hover); }

/* ── Main ── */
main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px 60px;
}

/* ── Stats Cards ── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 14px;
  margin-bottom: 28px;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
  text-align: center;
}
.stat-card .num {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--accent);
}
.stat-card .label {
  font-size: 0.82rem;
  color: var(--text-dim);
  margin-top: 4px;
}

/* ── Section Title ── */
.section-title {
  font-size: 1.15rem;
  font-weight: 600;
  margin: 28px 0 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.section-title::before {
  content: "";
  width: 4px;
  height: 20px;
  background: var(--accent);
  border-radius: 2px;
}

/* ── Category Grid ── */
.cat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 28px;
}
.cat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.cat-card:hover {
  border-color: var(--accent);
  background: var(--bg-hover);
  text-decoration: none;
}
.cat-card .cat-name { font-weight: 600; font-size: 0.95rem; }
.cat-card .cat-count {
  font-size: 0.85rem;
  color: var(--text-dim);
  background: var(--accent-soft);
  padding: 2px 10px;
  border-radius: 12px;
}

/* ── Track Table ── */
.track-table-wrap {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.track-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.track-table th {
  background: var(--bg-hover);
  padding: 10px 14px;
  text-align: left;
  font-weight: 600;
  color: var(--text-dim);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.track-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
.track-table tr:last-child td { border-bottom: none; }
.track-table tr:hover { background: var(--bg-hover); }
.track-table .track-name {
  color: var(--text);
  font-weight: 500;
  word-break: break-all;
}
.track-table .track-name:hover { color: var(--accent); }
.track-table .col-id {
  color: var(--text-faint);
  font-size: 0.8rem;
  white-space: nowrap;
  width: 70px;
}
.track-table .col-size {
  color: var(--text-dim);
  white-space: nowrap;
  width: 90px;
}
.track-table .col-time {
  color: var(--text-dim);
  white-space: nowrap;
  width: 130px;
}
.track-table .col-tags { width: 120px; }

/* ── Action Buttons ── */
.track-table .col-actions { width: 130px; white-space: nowrap; }
.act-btn {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 5px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-right: 4px;
  text-decoration: none;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
}
.act-listen {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.35);
}
.act-listen:hover { background: var(--accent); color: #fff; text-decoration: none; }
.act-download {
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.35);
  transition: all 0.2s ease;
}
.act-download:hover {
  background: linear-gradient(135deg, #10b981, #06b6d4);
  color: #fff;
  text-decoration: none;
  box-shadow: 0 3px 10px rgba(16, 185, 129, 0.4);
  transform: translateY(-1px);
}

/* ── 页内波纹播放器（仿 dj024：左控制+时间 / 中波形进度 / 右音量+循环+关闭；适配浏览器不遮挡）── */
body { padding-bottom: 76px; }
.player-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(9, 13, 24, 0.94);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid rgba(16, 185, 129, 0.28);
  padding: 9px 18px;
  display: flex;
  align-items: center;
  gap: 18px;
  z-index: 200;
  box-shadow: 0 -4px 26px rgba(0, 0, 0, 0.5);
}
.player-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
}
.player-mid {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.player-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.player-info { min-width: 0; }
.player-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.player-status { font-size: 0.75rem; color: var(--warn); margin-top: 2px; }
.player-status a { color: var(--accent); text-decoration: underline; }
.player-wave {
  width: 100%;
  height: 46px;
  background: rgba(16, 185, 129, 0.05);
  border: 1px solid rgba(16, 185, 129, 0.18);
  border-radius: 10px;
  cursor: pointer;
  box-shadow: inset 0 0 20px rgba(16, 185, 129, 0.07);
}
.player-toggle {
  background: linear-gradient(135deg, #10b981, #06b6d4);
  color: #fff;
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  font-size: 0.9rem;
  cursor: pointer;
  flex-shrink: 0;
  box-shadow: 0 3px 12px rgba(16, 185, 129, 0.4);
  transition: background 0.15s, transform 0.1s;
}
.player-toggle:hover { filter: brightness(1.12); transform: scale(1.06); }
.player-time {
  font-size: 0.72rem;
  color: var(--text-dim);
  white-space: nowrap;
  min-width: 84px;
  text-align: center;
}
.player-btn {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #a7f3d0;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  font-size: 0.95rem;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s;
}
.player-btn:hover { background: rgba(16, 185, 129, 0.25); }
.player-btn.on { background: var(--accent); color: #fff; border-color: var(--accent); }
.player-close {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 1.3rem;
  cursor: pointer;
  padding: 4px 8px;
  line-height: 1;
}
.player-close:hover { color: var(--text); }

/* 适配窄屏（不破版、不遮挡） */
@media (max-width: 860px) {
  body { padding-bottom: 70px; }
  .player-bar { padding: 8px 12px; gap: 12px; }
  .player-wave { height: 40px; }
  .player-status { display: none; }
  .player-toggle { width: 36px; height: 36px; }
}
@media (max-width: 620px) {
  .player-time { display: none; }
  .player-btn { width: 32px; height: 32px; font-size: 0.85rem; }
  .player-name { font-size: 0.75rem; }
}

/* ── Tags ── */
.tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
  margin-right: 4px;
}
.tag-single { background: rgba(59,130,246,0.15); color: #60a5fa; }
.tag-mashup { background: rgba(245,158,11,0.15); color: #fbbf24; }
.tag-zh { background: rgba(16,185,129,0.15); color: #34d399; }
.tag-en { background: rgba(168,85,247,0.15); color: #c084fc; }
.tag-other { background: rgba(107,114,128,0.15); color: #9ca3af; }
.tag-band { background: rgba(139,92,246,0.18); color: #c4b5fd; }

/* ── Pagination ── */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin-top: 20px;
  flex-wrap: wrap;
}
.pagination button, .pagination span {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text-dim);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.15s;
}
.pagination button:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.pagination .current {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.pagination .page-info {
  border: none;
  background: none;
  color: var(--text-faint);
}

/* ── Loading ── */
.loading {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-dim);
}
.loading .spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Date Archive ── */
.date-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}
.date-item {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;
}
.date-item:hover {
  border-color: var(--accent);
  text-decoration: none;
}
.date-item .d { font-weight: 600; font-size: 0.9rem; }
.date-item .c { font-size: 0.75rem; color: var(--text-dim); margin-top: 2px; }

/* ── Filter Bar ── */
.filter-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.filter-bar select {
  padding: 7px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text);
  font-size: 0.85rem;
  outline: none;
  cursor: pointer;
}
.filter-bar .result-count {
  margin-left: auto;
  color: var(--text-dim);
  font-size: 0.85rem;
}

/* ── Footer ── */
footer {
  text-align: center;
  padding: 24px 20px;
  color: var(--text-faint);
  font-size: 0.8rem;
  border-top: 1px solid var(--border);
}

/* ── Breadcrumb ── */
.breadcrumb {
  font-size: 0.85rem;
  color: var(--text-dim);
  margin-bottom: 16px;
}
.breadcrumb a { color: var(--text-dim); }
.breadcrumb a:hover { color: var(--accent); }
.breadcrumb .sep { margin: 0 6px; }

/* ── 注册/登录模态框（白牌） ── */
.auth-overlay {
  position: fixed;
  inset: 0;
  background: rgba(5, 7, 12, 0.72);
  backdrop-filter: blur(6px);
  z-index: 400;
  display: none;
  align-items: center;
  justify-content: center;
}
.auth-overlay.show { display: flex; }
.auth-modal {
  width: min(420px, 92vw);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: 0 18px 60px rgba(0,0,0,0.6);
  overflow: hidden;
  animation: authIn 0.22s ease-out;
}
@keyframes authIn {
  from { opacity: 0; transform: translateY(14px) scale(0.98); }
  to { opacity: 1; transform: none; }
}
.auth-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
}
.auth-head .t {
  font-size: 1.02rem;
  font-weight: 700;
}
.auth-close {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 1.35rem;
  cursor: pointer;
  line-height: 1;
  padding: 2px 8px;
}
.auth-close:hover { color: var(--text); }
.auth-tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
}
.auth-tab {
  flex: 1;
  padding: 11px 0;
  text-align: center;
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
}
.auth-tab.on {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
.auth-body { padding: 18px 20px 22px; }
.auth-field { margin-bottom: 13px; }
.auth-field label {
  display: block;
  font-size: 0.8rem;
  color: var(--text-dim);
  margin-bottom: 5px;
}
.auth-field input {
  width: 100%;
  padding: 9px 13px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.15s;
}
.auth-field input:focus { border-color: var(--accent); }
.auth-submit {
  width: 100%;
  padding: 11px 0;
  border: none;
  border-radius: 9px;
  background: var(--accent);
  color: #fff;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  margin-top: 6px;
  transition: background 0.15s, opacity 0.15s;
}
.auth-submit:hover { background: var(--accent-hover); }
.auth-submit:disabled { opacity: 0.55; cursor: wait; }
.auth-note {
  margin-top: 13px;
  font-size: 0.78rem;
  color: var(--text-faint);
  line-height: 1.7;
}
.auth-note b { color: var(--warn); font-weight: 600; }
.auth-note a { color: var(--accent); text-decoration: underline; }

/* ── 曲目详情页 ── */
.detail-wrap {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 24px 26px;
  max-width: 860px;
}
.detail-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text);
  word-break: break-all;
  margin-bottom: 18px;
  line-height: 1.5;
}
.detail-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.detail-meta .m {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
}
.detail-meta .m .k {
  font-size: 0.75rem;
  color: var(--text-faint);
  margin-bottom: 4px;
}
.detail-meta .m .v {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text);
  word-break: break-all;
}
.detail-links { margin-bottom: 20px; font-size: 0.85rem; }
.detail-links a { color: var(--accent); margin-right: 14px; }
.detail-links a.track-download {
  display: inline-block;
  background: linear-gradient(135deg, #10b981, #06b6d4);
  color: #fff;
  padding: 7px 18px;
  border-radius: 9px;
  font-weight: 600;
  text-decoration: none;
  box-shadow: 0 3px 12px rgba(16, 185, 129, 0.35);
  transition: all 0.2s ease;
  vertical-align: middle;
}
.detail-links a.track-download:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 18px rgba(6, 182, 212, 0.5);
  filter: brightness(1.08);
}

/* ── 详情页内嵌波纹播放器 ── */
.detail-player-box {
  background: rgba(9, 13, 24, 0.92);
  border: 1px solid rgba(16, 185, 129, 0.28);
  border-radius: 12px;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  box-shadow: 0 4px 26px rgba(0, 0, 0, 0.35);
}

/* ── Toast 提示 ── */
.toast {
  position: fixed;
  right: 20px;
  bottom: 90px;
  background: var(--bg-card);
  border: 1px solid var(--accent);
  border-radius: 10px;
  padding: 12px 18px;
  font-size: 0.85rem;
  color: var(--text);
  box-shadow: 0 8px 30px rgba(0,0,0,0.5);
  z-index: 500;
  opacity: 0;
  transform: translateY(8px);
  transition: all 0.25s;
  max-width: 320px;
}
.toast.show { opacity: 1; transform: none; }
.toast a { color: var(--accent); text-decoration: underline; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .header-inner { padding: 10px 14px; gap: 10px; }
  .search-box { max-width: 100%; order: 3; }
  main { padding: 16px 12px 40px; }
  .track-table .col-id, .track-table .col-tags { display: none; }
  .track-table th, .track-table td { padding: 8px 10px; font-size: 0.82rem; }
  .stat-card .num { font-size: 1.4rem; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .player-bar { flex-wrap: wrap; padding: 8px 12px; }
  .player-wave { width: 100%; }
  .player-time { display: none; }
}
"""


def generate_js(total_tracks, page_size, latest_ids):
    """生成客户端 JS。latest_ids 是首页预载曲目的 id 列表。"""
    return f"""/* ===== 9GDJ DJ 索引 — 客户端逻辑 ===== */
(function() {{
  'use strict';

  const PAGE_SIZE = {page_size};
  let ALL_TRACKS = null;
  let STATS = null;
  let DATES = null;
  let currentPage = 1;
  let filtered = null;

  const FORMAT_NAMES = ['单曲', '串烧'];
  const LANG_NAMES = ['中文', '英文', '其他'];

  // ── 工具 ──
  function $(sel) {{ return document.querySelector(sel); }}
  function el(tag, attrs, children) {{
    const e = document.createElement(tag);
    if (attrs) for (const k in attrs) {{
      if (k === 'class') e.className = attrs[k];
      else if (k === 'text') e.textContent = attrs[k];
      else e.setAttribute(k, attrs[k]);
    }}
    if (children) children.forEach(c => e.appendChild(c));
    return e;
  }}

  function getQuery() {{
    const q = {{}};
    new URLSearchParams(window.location.search).forEach((v, k) => q[k] = v);
    return q;
  }}

  function setQuery(params) {{
    const qs = new URLSearchParams(params).toString();
    const url = qs ? '?' + qs : window.location.pathname;
    window.history.pushState({{}}, '', url);
  }}

  // ── 数据加载 ──
  async function loadData() {{
    showLoading('正在加载曲目数据...');
    try {{
      const [t, s, d] = await Promise.all([
        fetch('data/tracks.json').then(r => r.json()),
        fetch('data/stats.json').then(r => r.json()),
        fetch('data/dates.json').then(r => r.json())
      ]);
      ALL_TRACKS = t;
      STATS = s;
      DATES = d;
      hideLoading();
      return true;
    }} catch (e) {{
      showLoading('数据加载失败: ' + e.message);
      return false;
    }}
  }}

  function showLoading(msg) {{
    const m = $('#main');
    m.innerHTML = '<div class="loading"><div class="spinner"></div>' + (msg || '加载中...') + '</div>';
  }}
  function hideLoading() {{ $('#main').innerHTML = ''; }}

  // ── 渲染曲目表格 ──
  function renderTrackTable(tracks, container, opts) {{
    opts = opts || {{}};
    if (!tracks || tracks.length === 0) {{
      container.innerHTML = '<div class="loading">没有找到匹配的曲目</div>';
      return;
    }}
    const wrap = el('div', {{class: 'track-table-wrap'}});
    const table = el('table', {{class: 'track-table'}});
    const thead = el('thead');
    thead.appendChild(el('tr', null, [
      el('th', {{text: '#'}}),
      el('th', {{text: '文件名'}}),
      el('th', {{text: '大小'}}),
      el('th', {{text: '时间'}}),
      el('th', {{text: '标签'}}),
      el('th', {{text: '操作'}}),
    ]));
    table.appendChild(thead);
    const tbody = el('tbody');
    tracks.forEach(t => {{
      const tr = el('tr');
      tr.appendChild(el('td', {{class: 'col-id', text: t.i}}));
      const nameTd = el('td');
      const nameA = el('a', {{
        href: '?id=' + t.i,
        class: 'track-name',
        text: t.n
      }});
      nameA.dataset.id = t.i;
      nameTd.appendChild(nameA);
      tr.appendChild(nameTd);
      tr.appendChild(el('td', {{class: 'col-size', text: t.s != null ? t.s + ' MiB' : '-'}}));
      tr.appendChild(el('td', {{class: 'col-time', text: t.t}}));
      const tagTd = el('td', {{class: 'col-tags'}});
      tagTd.appendChild(el('span', {{class: 'tag tag-' + (t.f === 1 ? 'mashup' : 'single'), text: FORMAT_NAMES[t.f]}}));
      tagTd.appendChild(el('span', {{class: 'tag tag-' + (t.l === 0 ? 'zh' : t.l === 1 ? 'en' : 'other'), text: LANG_NAMES[t.l]}}));
      tr.appendChild(tagTd);
      const actTd = el('td', {{class: 'col-actions'}});
      const dlUrl = API + '/api/download/' + t.i + '?cid=' + getCid();
      const listenBtn = el('button', {{type: 'button', class: 'act-btn act-listen', text: '试听'}});
      listenBtn.dataset.id = t.i;
      listenBtn.dataset.name = t.n;
      listenBtn.dataset.au = t.au || '';
      actTd.appendChild(listenBtn);
      actTd.appendChild(el('a', {{href: dlUrl, class: 'act-btn act-download', text: '下载', download: t.n}}));
      tr.appendChild(actTd);
      tbody.appendChild(tr);
    }});
    table.appendChild(tbody);
    wrap.appendChild(table);
    container.appendChild(wrap);
  }}

  // ── 分页 ──
  function renderPagination(total, page, container, onChange) {{
    const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
    const pag = el('div', {{class: 'pagination'}});

    const prev = el('button', {{text: '上一页'}});
    prev.disabled = page <= 1;
    prev.onclick = () => onChange(page - 1);
    pag.appendChild(prev);

    // 页码逻辑：显示当前页附近
    const pages = [];
    const range = 2;
    for (let p = 1; p <= totalPages; p++) {{
      if (p === 1 || p === totalPages || (p >= page - range && p <= page + range)) {{
        pages.push(p);
      }} else if (pages[pages.length - 1] !== '...') {{
        pages.push('...');
      }}
    }}
    pages.forEach(p => {{
      if (p === '...') {{
        pag.appendChild(el('span', {{class: 'page-info', text: '...'}}));
      }} else {{
        const btn = el('button', {{text: p, class: p === page ? 'current' : ''}});
        btn.onclick = () => onChange(p);
        pag.appendChild(btn);
      }}
    }});

    const next = el('button', {{text: '下一页'}});
    next.disabled = page >= totalPages;
    next.onclick = () => onChange(page + 1);
    pag.appendChild(next);

    pag.appendChild(el('span', {{class: 'page-info', text: page + '/' + totalPages + ' 页 · 共 ' + total + ' 条'}}));
    container.appendChild(pag);
  }}

  // ── 首页 ──
  function renderHome() {{
    const m = $('#main');
    m.innerHTML = '';

    // 统计卡片
    const statsGrid = el('div', {{class: 'stats-grid'}});
    const cards = [
      [STATS.total, '曲目总数'],
      [STATS.format.single || 0, '单曲'],
      [STATS.format.mashup || 0, '串烧'],
      [STATS.language.zh || 0, '中文'],
      [STATS.language.en || 0, '英文'],
      [STATS.today_count || 0, '今日新增'],
    ];
    cards.forEach(([num, label]) => {{
      const card = el('div', {{class: 'stat-card'}});
      card.appendChild(el('div', {{class: 'num', text: num.toLocaleString()}}));
      card.appendChild(el('div', {{class: 'label', text: label}}));
      statsGrid.appendChild(card);
    }});
    m.appendChild(statsGrid);

    // 分类入口
    m.appendChild(el('div', {{class: 'section-title', text: '分类浏览'}}));
    const catGrid = el('div', {{class: 'cat-grid'}});
    const cats = [
      ['全部单曲', 'format=single', STATS.format.single || 0],
      ['全部串烧', 'format=mashup', STATS.format.mashup || 0],
      ['中文单曲', 'format=single&lang=zh', STATS.combo.zh_single || 0],
      ['英文单曲', 'format=single&lang=en', STATS.combo.en_single || 0],
      ['中文串烧', 'format=mashup&lang=zh', STATS.combo.zh_mashup || 0],
      ['英文串烧', 'format=mashup&lang=en', STATS.combo.en_mashup || 0],
    ];
    cats.forEach(([name, qs, count]) => {{
      const card = el('a', {{href: '?' + qs, class: 'cat-card'}});
      card.appendChild(el('span', {{class: 'cat-name', text: name}}));
      card.appendChild(el('span', {{class: 'cat-count', text: count.toLocaleString()}}));
      catGrid.appendChild(card);
    }});
    m.appendChild(catGrid);

    // 最新入库
    m.appendChild(el('div', {{class: 'section-title', text: '最新入库'}}));
    const latest = ALL_TRACKS.slice(0, {LATEST_ON_HOME});
    renderTrackTable(latest, m);
    const moreLink = el('div', {{style: 'text-align:center;margin-top:16px;'}});
    moreLink.appendChild(el('a', {{href: '?view=all', text: '查看全部 →'}}));
    m.appendChild(moreLink);

    // 日期归档入口
    m.appendChild(el('div', {{class: 'section-title', text: '按日期归档'}}));
    const dateLink = el('div');
    dateLink.appendChild(el('a', {{href: '?view=dates', text: '浏览 ' + DATES.length + ' 个入库日期 →'}}));
    m.appendChild(dateLink);

    updateNav('home');
  }}

  // ── 列表视图（分类/搜索/全部）──
  function renderList() {{
    const q = getQuery();
    const m = $('#main');
    m.innerHTML = '';

    // 面包屑
    const bc = el('div', {{class: 'breadcrumb'}});
    bc.appendChild(el('a', {{href: '?', text: '首页'}}));
    bc.appendChild(el('span', {{class: 'sep', text: '/'}}));
    let title = '全部曲目';
    if (q.format) title = (q.format === 'mashup' ? '串烧' : '单曲');
    if (q.lang) title = (q.lang === 'zh' ? '中文' : q.lang === 'en' ? '英文' : '其他') + title;
    if (q.q) title = '搜索: "' + q.q + '"';
    if (q.date) title = q.date + ' 入库';
    bc.appendChild(el('span', {{text: title}}));
    m.appendChild(bc);

    // 过滤
    let result = ALL_TRACKS;
    if (q.format) result = result.filter(t => (q.format === 'mashup' ? t.f === 1 : t.f === 0));

    if (q.lang) result = result.filter(t => (q.lang === 'zh' ? t.l === 0 : q.lang === 'en' ? t.l === 1 : t.l === 2));
    if (q.date) result = result.filter(t => t.d === q.date);
    if (q.q) {{
      const kw = q.q.toLowerCase();
      result = result.filter(t => t.n.toLowerCase().includes(kw));
    }}
    filtered = result;

    // 过滤栏
    const bar = el('div', {{class: 'filter-bar'}});
    const fmtSel = el('select');
    [['', '全部格式'], ['single', '单曲'], ['mashup', '串烧']].forEach(([v, label]) => {{
      const o = el('option', {{value: v, text: label}});
      if (q.format === v) o.selected = true;
      fmtSel.appendChild(o);
    }});
    fmtSel.onchange = () => {{ const nq = getQuery(); nq.format = fmtSel.value; if(!nq.format) delete nq.format; nq.page=1; setQuery(nq); renderList(); }};
    bar.appendChild(fmtSel);

    const langSel = el('select');
    [['', '全部语言'], ['zh', '中文'], ['en', '英文'], ['other', '其他']].forEach(([v, label]) => {{
      const o = el('option', {{value: v, text: label}});
      if (q.lang === v) o.selected = true;
      langSel.appendChild(o);
    }});
    langSel.onchange = () => {{ const nq = getQuery(); nq.lang = langSel.value; if(!nq.lang) delete nq.lang; nq.page=1; setQuery(nq); renderList(); }};
    bar.appendChild(langSel);

    bar.appendChild(el('span', {{class: 'result-count', text: '共 ' + result.length.toLocaleString() + ' 条'}}));
    m.appendChild(bar);

    // 分页
    const page = parseInt(q.page) || 1;
    const start = (page - 1) * PAGE_SIZE;
    const pageTracks = result.slice(start, start + PAGE_SIZE);
    renderTrackTable(pageTracks, m);
    renderPagination(result.length, page, m, (p) => {{
      const nq = getQuery(); nq.page = p; setQuery(nq); renderList();
      window.scrollTo({{top: 0, behavior: 'smooth'}});
    }});

    updateNav(q.format || q.q || q.date ? 'list' : 'all');
  }}

  // ── 日期归档 ──
  function renderDates() {{
    const m = $('#main');
    m.innerHTML = '';
    const bc = el('div', {{class: 'breadcrumb'}});
    bc.appendChild(el('a', {{href: '?', text: '首页'}}));
    bc.appendChild(el('span', {{class: 'sep', text: '/'}}));
    bc.appendChild(el('span', {{text: '日期归档'}}));
    m.appendChild(bc);
    m.appendChild(el('div', {{class: 'section-title', text: '按入库日期浏览 (' + DATES.length + ' 天)'}}));
    const grid = el('div', {{class: 'date-grid'}});
    DATES.forEach(([d, count]) => {{
      const item = el('a', {{href: '?date=' + d, class: 'date-item'}});
      item.appendChild(el('div', {{class: 'd', text: d}}));
      item.appendChild(el('div', {{class: 'c', text: count + ' 首'}}));
      grid.appendChild(item);
    }});
    m.appendChild(grid);
    updateNav('dates');
  }}

  // ── 曲目详情（站内底层页）──
  function renderDetail(id) {{
    const m = $('#main');
    m.innerHTML = '';
    const t = ALL_TRACKS.find(x => String(x.i) === String(id));
    if (!t) {{
      m.appendChild(el('div', {{class: 'loading', text: '未找到该曲目 (ID=' + id + ')'}}));
      return;
    }}
    const bc = el('div', {{class: 'breadcrumb'}});
    bc.appendChild(el('a', {{href: '?', text: '首页'}}));
    bc.appendChild(el('span', {{class: 'sep', text: '/'}}));
    bc.appendChild(el('span', {{text: '曲目详情'}}));
    m.appendChild(bc);

    const wrap = el('div', {{class: 'detail-wrap'}});
    wrap.appendChild(el('div', {{class: 'detail-title', text: t.n}}));

    const meta = el('div', {{class: 'detail-meta'}});
    const fmtName = FORMAT_NAMES[t.f === 1 ? 1 : 0];
    const langName = LANG_NAMES[t.l === 0 ? 0 : t.l === 1 ? 1 : 2];
    [['编号', String(t.i)], ['大小', t.s != null ? t.s + ' MiB' : '-'], ['入库时间', t.t || '-'], ['格式', fmtName], ['语言', langName]].forEach(([k, v]) => {{
      const cell = el('div', {{class: 'm'}});
      cell.appendChild(el('div', {{class: 'k', text: k}}));
      cell.appendChild(el('div', {{class: 'v', text: v}}));
      meta.appendChild(cell);
    }});
    wrap.appendChild(meta);

    const links = el('div', {{class: 'detail-links'}});
    if (t.u) links.appendChild(el('a', {{href: t.u, target: '_blank', rel: 'noopener', text: '来源站页面 ↗'}}));
    links.appendChild(el('a', {{href: API + '/api/download/' + t.i + '?cid=' + getCid(), class: 'track-download', text: '下载', download: t.n}}));
    wrap.appendChild(links);

    // 内嵌波纹播放器（播放爬虫抓取的音频直连地址；无直链时回退官方接口）
    wrap.appendChild(detailPlayer.render(t.i, t.n, t.au || ''));
    m.appendChild(wrap);
    updateNav('home');
  }}

  // ── 详情页内嵌波纹播放器（独立于底部播放栏）──
  const detailPlayer = (function() {{
    const box = el('div', {{class: 'detail-player-box'}});
    // 左：播放控制 + 时间（仿 dj024 三段式，与底部播放栏同款）
    const left = el('div', {{class: 'player-left'}});
    const btnPlay = el('button', {{type: 'button', class: 'player-toggle', text: '▶', title: '播放 / 暂停'}});
    const timeEl = el('div', {{class: 'player-time', text: '0:00 / 0:00'}});
    left.appendChild(btnPlay);
    left.appendChild(timeEl);
    // 中：曲名/状态 + 五彩波形（蒙层进度）
    const mid = el('div', {{class: 'player-mid'}});
    const nameEl = el('div', {{class: 'player-name', text: ''}});
    const statusEl = el('div', {{class: 'player-status'}});
    const info = el('div', {{class: 'player-info'}});
    info.appendChild(nameEl);
    info.appendChild(statusEl);
    mid.appendChild(info);
    const canvas = el('canvas', {{class: 'player-wave'}});
    canvas.width = 460;
    canvas.height = 48;
    const ctx = canvas.getContext('2d');
    mid.appendChild(canvas);
    // 右：音量 + 单曲循环
    const right = el('div', {{class: 'player-right'}});
    const muteBtn = el('button', {{type: 'button', class: 'player-btn', text: '🔊', title: '静音'}});
    const loopBtn = el('button', {{type: 'button', class: 'player-btn', text: '🔁', title: '单曲循环：关'}});
    right.appendChild(muteBtn);
    right.appendChild(loopBtn);
    box.appendChild(left);
    box.appendChild(mid);
    box.appendChild(right);

    const audio = new Audio();
    audio.preload = 'none';
    audio.controls = false;

    let animId = null;
    let failed = false;
    let useDirect = false;
    let trackId = null;

    function fmt(s) {{
      if (!isFinite(s) || s < 0) s = 0;
      return Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
    }}

    function draw() {{
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);
      const t = performance.now() / 1000;
      const bars = 60;
      const bw = W / bars;
      const playing = !audio.paused && !audio.ended && !failed && audio.readyState > 0;
      for (let i = 0; i < bars; i++) {{
        const phase = (i / bars) * Math.PI * 2 + t * (playing ? 7 : 2.2);
        const amp = playing ? 0.92 : 0.16;
        const h = (Math.sin(phase) * 0.5 + 0.5) * amp * H * 0.78 + (playing ? 5 : 2);
        const x = i * bw + bw * 0.18;
        const hue = ((i / bars) * 360 + t * 40) % 360;
        const grad = ctx.createLinearGradient(0, H / 2 - h, 0, H / 2 + h);
        grad.addColorStop(0, 'hsl(' + hue + ' 90% 65%)');
        grad.addColorStop(0.5, 'hsl(' + ((hue + 45) % 360) + ' 95% 55%)');
        grad.addColorStop(1, 'hsl(' + ((hue + 90) % 360) + ' 90% 60%)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(x, H / 2 - h / 2, bw * 0.5, h, 3);
        else ctx.rect(x, H / 2 - h / 2, bw * 0.5, h);
        ctx.fill();
      }}
      const prog = audio.duration > 0 ? Math.min(1, audio.currentTime / audio.duration) : 0;
      if (prog < 1) {{
        ctx.fillStyle = 'rgba(8,12,24,0.55)';
        ctx.fillRect(prog * W, 0, W * (1 - prog), H);
      }}
      if (prog > 0) {{
        ctx.fillStyle = 'rgba(255,255,255,0.85)';
        ctx.fillRect(prog * W - 1.5, 0, 3, H);
      }}
      animId = requestAnimationFrame(draw);
    }}

    function stopAnim() {{
      if (animId) {{ cancelAnimationFrame(animId); animId = null; }}
    }}

    function play(id, name, au) {{
      trackId = id;
      failed = false;
      useDirect = !!(au && au.indexOf('http') === 0);
      nameEl.textContent = name;
      statusEl.textContent = '';
      statusEl.appendChild(document.createTextNode(useDirect ? '正在连接音频源…（来源站直连，无需登录）' : '正在连接音频源…（站内代理）'));
      btnPlay.textContent = '▶';
      timeEl.textContent = '0:00 / 0:00';
      audio.src = useDirect ? au : API + '/api/audio/' + id + '?cid=' + getCid();
      audio.load();
      if (!animId) draw();
      const p = audio.play();
      if (p && p.catch) p.catch(function() {{}});
    }}

    function stop() {{
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
      stopAnim();
      btnPlay.textContent = '▶';
      nameEl.textContent = '';
      statusEl.textContent = '';
    }}

    function markFailed() {{
      failed = true;
      btnPlay.textContent = '▶';
      statusEl.textContent = '';
      if (useDirect) {{
        statusEl.appendChild(document.createTextNode('播放失败：音频源连接异常，请稍后重试。'));
      }} else {{
        statusEl.appendChild(document.createTextNode('播放失败：请确认已登录后再试。'));
      }}
    }}

    let muted = false;
    let loopOn = false;
    muteBtn.onclick = function() {{
      muted = !muted;
      audio.muted = muted;
      muteBtn.textContent = muted ? '🔇' : '🔊';
    }};
    loopBtn.onclick = function() {{
      loopOn = !loopOn;
      audio.loop = loopOn;
      loopBtn.textContent = loopOn ? '🔁' : '🔁';
      loopBtn.title = loopOn ? '单曲循环：开' : '单曲循环：关';
      if (loopOn) {{ loopBtn.style.color = '#fbbf24'; }} else {{ loopBtn.style.color = ''; }}
    }};
    btnPlay.onclick = function() {{
      if (audio.src && !audio.paused) {{ audio.pause(); return; }}
      if (!animId) draw();
      const p = audio.play();
      if (p && p.catch) p.catch(function(e) {{
        failed = true;
        statusEl.textContent = '';
        statusEl.appendChild(document.createTextNode('播放失败：' + (e && e.name ? e.name : '未知错误') + '，请点击播放键重试。'));
      }});
    }};
    audio.onplaying = function() {{ failed = false; btnPlay.textContent = '⏸'; statusEl.textContent = ''; }};
    audio.onpause = function() {{ btnPlay.textContent = '▶'; }};
    audio.onended = function() {{ btnPlay.textContent = '▶'; }};
    audio.onerror = function() {{ markFailed(); }};
    audio.addEventListener('timeupdate', function() {{
      const d = isFinite(audio.duration) ? audio.duration : 0;
      timeEl.textContent = fmt(audio.currentTime) + ' / ' + fmt(d);
    }});
    canvas.addEventListener('click', function(e) {{
      if (!isFinite(audio.duration) || audio.duration <= 0) return;
      const rect = canvas.getBoundingClientRect();
      audio.currentTime = ((e.clientX - rect.left) / rect.width) * audio.duration;
    }});
    // 整块播放器区域点击也可播放/暂停（canvas 由上面 seek 逻辑接管）
    box.addEventListener('click', function(e) {{
      if (e.target === canvas) return;
      if (!audio.src) return;
      if (!audio.paused) {{ audio.pause(); return; }}
      if (!animId) draw();
      const p = audio.play();
      if (p && p.catch) p.catch(function(er) {{
        failed = true;
        statusEl.textContent = '';
        statusEl.appendChild(document.createTextNode('播放失败：' + (er && er.name ? er.name : '未知错误') + '，请重试。'));
      }});
    }});

    function render(id, name, au) {{
      // 预置音频源但不自动播放（避免浏览器自动播放策略拦截）
      trackId = id;
      failed = false;
      useDirect = !!(au && au.indexOf('http') === 0);
      nameEl.textContent = name;
      statusEl.textContent = '';
      statusEl.appendChild(document.createTextNode(useDirect ? '点击播放（来源站直连）' : '点击播放（站内代理）'));
      btnPlay.textContent = '▶';
      timeEl.textContent = '0:00 / 0:00';
      audio.src = useDirect ? au : API + '/api/audio/' + id + '?cid=' + getCid();
      audio.load();
      if (!animId) draw();
      return box;
    }}
    return {{render: render, stop: stop}};
  }})();

  // ── 导航高亮 ──
  function updateNav(active) {{
    document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
    const map = {{home: 'nav-home', all: 'nav-all', dates: 'nav-dates'}};
    const id = map[active];
    if (id) {{ const el = document.getElementById(id); if (el) el.classList.add('active'); }}
  }}

  // ── 路由 ──
  function route() {{
    const q = getQuery();
    if (q.id) {{
      if (typeof player !== 'undefined' && player) player.hide();
      renderDetail(q.id);
    }} else {{
      if (typeof detailPlayer !== 'undefined' && detailPlayer) detailPlayer.stop();
      if (q.view === 'dates' || q.date) {{
        if (q.date) renderList();
        else renderDates();
      }} else if (q.format || q.lang || q.q || q.view === 'all' || q.page) {{
        renderList();
      }} else {{
        renderHome();
      }}
    }}
  }}

  // ── Toast ──
  function toast(msg) {{
    let t = document.getElementById('toast');
    if (!t) {{
      t = el('div', {{class: 'toast', id: 'toast'}});
      document.body.appendChild(t);
    }}
    t.innerHTML = '';
    t.appendChild(document.createTextNode(msg));
    t.classList.add('show');
    clearTimeout(t._tm);
    t._tm = setTimeout(() => t.classList.remove('show'), 3200);
  }}

  // ── 登录态（本地标记；官方页完成登录后确认）──
  // 部署配置：window.API_BASE 由 index.html 注入（空=同源本地；GitHub Pages 部署时填后端地址）
  const API = window.API_BASE || '';
  function getCid() {{
    let c = localStorage.getItem('panda_cid');
    if (!c) {{
      c = 'c' + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem('panda_cid', c);
    }}
    return c;
  }}
  function isAuthed() {{ return localStorage.getItem('panda_auth') === '1'; }}
  function setAuthed(v, name) {{
    if (v) {{
      localStorage.setItem('panda_auth', '1');
    }} else {{
      localStorage.removeItem('panda_auth');
    }}
    refreshAuthUI();
  }}
  function refreshAuthUI() {{
    // 昵称显示模块已移除（仅保留自动授权标识）
  }}

  // ── 搜索 ──
  function setupSearch() {{
    const input = $('#search-input');
    const btn = $('#search-btn');
    function doSearch() {{
      const val = input.value.trim();
      if (val) {{
        setQuery({{q: val, page: 1}});
        route();
      }}
    }}
    btn.onclick = doSearch;
    input.addEventListener('keydown', e => {{ if (e.key === 'Enter') doSearch(); }});
  }}

  // ── 页内波纹播放器（科技风可视化；音频流对接音频接口，需登录）──
  const player = (function() {{
    const bar = el('div', {{class: 'player-bar', style: 'display:none;'}});
    // 左：播放控制 + 时间（仿 dj024 三段式）
    const left = el('div', {{class: 'player-left'}});
    const btnPlay = el('button', {{type: 'button', class: 'player-toggle', text: '▶', title: '播放 / 暂停'}});
    const timeEl = el('div', {{class: 'player-time', text: '0:00 / 0:00'}});
    left.appendChild(btnPlay);
    left.appendChild(timeEl);
    // 中：曲名/状态 + 波形进度
    const mid = el('div', {{class: 'player-mid'}});
    const nameEl = el('div', {{class: 'player-name', text: ''}});
    const statusEl = el('div', {{class: 'player-status'}});
    const info = el('div', {{class: 'player-info'}});
    info.appendChild(nameEl);
    info.appendChild(statusEl);
    mid.appendChild(info);
    const canvas = el('canvas', {{class: 'player-wave'}});
    canvas.width = 460;
    canvas.height = 48;
    const ctx = canvas.getContext('2d');
    mid.appendChild(canvas);
    // 右：音量 + 单曲循环 + 关闭
    const right = el('div', {{class: 'player-right'}});
    const muteBtn = el('button', {{type: 'button', class: 'player-btn', text: '🔊', title: '静音'}});
    const loopBtn = el('button', {{type: 'button', class: 'player-btn', text: '🔁', title: '单曲循环：关'}});
    const closeBtn = el('button', {{type: 'button', class: 'player-close', text: '×', title: '关闭播放器'}});
    right.appendChild(muteBtn);
    right.appendChild(loopBtn);
    right.appendChild(closeBtn);
    bar.appendChild(left);
    bar.appendChild(mid);
    bar.appendChild(right);
    document.body.appendChild(bar);

    const audio = new Audio();
    audio.preload = 'none';
    audio.controls = false;

    let trackId = null;
    let animId = null;
    let failed = false;
    let useDirect = false;

    function fmt(s) {{
      if (!isFinite(s) || s < 0) s = 0;
      return Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
    }}

    function draw() {{
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);
      const t = performance.now() / 1000;
      const bars = 52;
      const bw = W / bars;
      const playing = !audio.paused && !audio.ended && !failed && audio.readyState > 0;
      for (let i = 0; i < bars; i++) {{
        const phase = (i / bars) * Math.PI * 2 + t * (playing ? 7 : 2.2);
        const amp = playing ? 0.9 : 0.16;
        const h = (Math.sin(phase) * 0.5 + 0.5) * amp * H * 0.78 + (playing ? 5 : 2);
        const x = i * bw + bw * 0.18;
        const hue = ((i / bars) * 360 + t * 40) % 360;
        const grad = ctx.createLinearGradient(0, H / 2 - h, 0, H / 2 + h);
        grad.addColorStop(0, 'hsl(' + hue + ' 90% 65%)');
        grad.addColorStop(0.5, 'hsl(' + ((hue + 45) % 360) + ' 95% 55%)');
        grad.addColorStop(1, 'hsl(' + ((hue + 90) % 360) + ' 90% 60%)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(x, H / 2 - h / 2, bw * 0.5, h, 3);
        else ctx.rect(x, H / 2 - h / 2, bw * 0.5, h);
        ctx.fill();
      }}
      const prog = audio.duration > 0 ? Math.min(1, audio.currentTime / audio.duration) : 0;
      if (prog < 1) {{
        ctx.fillStyle = 'rgba(8,12,24,0.55)';
        ctx.fillRect(prog * W, 0, W * (1 - prog), H);
      }}
      if (prog > 0) {{
        ctx.fillStyle = 'rgba(255,255,255,0.85)';
        ctx.fillRect(prog * W - 1.5, 0, 3, H);
      }}
      animId = requestAnimationFrame(draw);
    }}

    function stopAnim() {{
      if (animId) {{ cancelAnimationFrame(animId); animId = null; }}
    }}

    function show(id, name, au) {{
      trackId = id;
      failed = false;
      useDirect = !!(au && au.indexOf('http') === 0);
      nameEl.textContent = name;
      statusEl.textContent = '';
      statusEl.appendChild(document.createTextNode(useDirect ? '正在连接音频源…（来源站直连，无需登录）' : '正在连接音频源…（站内代理）'));
      btnPlay.textContent = '▶';
      timeEl.textContent = '0:00 / 0:00';
      audio.src = useDirect ? au : API + '/api/audio/' + id + '?cid=' + getCid();
      audio.load();
      bar.style.display = 'flex';
      if (!animId) draw();
      const p = audio.play();
      if (p && p.catch) p.catch(function() {{}});
    }}

    function hide() {{
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
      stopAnim();
      bar.style.display = 'none';
    }}

    function markFailed() {{
      failed = true;
      btnPlay.textContent = '▶';
      statusEl.textContent = '';
      if (useDirect) {{
        statusEl.appendChild(document.createTextNode('播放失败：音频源连接异常，请稍后重试。'));
      }} else {{
        statusEl.appendChild(document.createTextNode('播放失败：请确认已登录后再试。'));
      }}
    }}

    let muted = false;
    let loopOn = false;
    muteBtn.onclick = function() {{
      muted = !muted;
      audio.muted = muted;
      muteBtn.textContent = muted ? '🔇' : '🔊';
      muteBtn.title = muted ? '取消静音' : '静音';
    }};
    loopBtn.onclick = function() {{
      loopOn = !loopOn;
      audio.loop = loopOn;
      loopBtn.classList.toggle('on', loopOn);
      loopBtn.title = loopOn ? '单曲循环：开' : '单曲循环：关';
    }};
    closeBtn.onclick = hide;
    btnPlay.onclick = function() {{
      if (audio.paused) {{ const p = audio.play(); if (p && p.catch) p.catch(function() {{}}); }}
      else audio.pause();
    }};
    audio.onplaying = function() {{ failed = false; btnPlay.textContent = '⏸'; statusEl.textContent = ''; }};
    audio.onpause = function() {{ btnPlay.textContent = '▶'; }};
    audio.onended = function() {{ btnPlay.textContent = '▶'; }};
    audio.onerror = function() {{ markFailed(); }};
    audio.addEventListener('timeupdate', function() {{
      const d = isFinite(audio.duration) ? audio.duration : 0;
      timeEl.textContent = fmt(audio.currentTime) + ' / ' + fmt(d);
    }});
    canvas.addEventListener('click', function(e) {{
      if (!isFinite(audio.duration) || audio.duration <= 0) return;
      const rect = canvas.getBoundingClientRect();
      audio.currentTime = ((e.clientX - rect.left) / rect.width) * audio.duration;
    }});
    return {{show: show, hide: hide}};
  }})();

  // ── 注册/登录模态框（白牌） ──
  const auth = (function() {{
    const overlay = document.getElementById('auth-overlay');
    if (!overlay) return null;
    const tabs = overlay.querySelectorAll('.auth-tab');
    const formReg = document.getElementById('auth-form-register');
    const formLog = document.getElementById('auth-form-login');
    const titleEl = document.getElementById('auth-title');
    function switchTab(mode) {{
      tabs.forEach(t => t.classList.toggle('on', t.dataset.tab === mode));
      if (formReg) formReg.style.display = mode === 'register' ? '' : 'none';
      if (formLog) formLog.style.display = mode === 'login' ? '' : 'none';
      if (titleEl) titleEl.textContent = mode === 'register' ? '注册新账号' : '登录';
    }}
    function open(mode) {{
      switchTab(mode || 'register');
      overlay.classList.add('show');
    }}
    function close() {{ overlay.classList.remove('show'); }}
    function setNote(id, msg) {{ const n = document.getElementById(id); if (n) n.textContent = msg; }}
    function busy(btn, on) {{
      if (!btn) return;
      btn.disabled = on;
      btn.textContent = on ? '提交中…' : (btn.id === 'auth-submit-register' ? '注册' : '登录');
    }}
    async function submitRegister() {{
      const name = (document.getElementById('auth-name') || {{}}).value || '';
      const email = (document.getElementById('auth-email') || {{}}).value || '';
      const pass = (document.getElementById('auth-pass') || {{}}).value || '';
      const pass2 = (document.getElementById('auth-pass2') || {{}}).value || '';
      if (!name || !email || !pass || !pass2) {{ setNote('auth-note-register', '请填写完整信息。'); return; }}
      if (pass !== pass2) {{ setNote('auth-note-register', '两次输入的密码不一致。'); return; }}
      const btn = document.getElementById('auth-submit-register');
      busy(btn, true);
      try {{
        const r = await fetch(API + '/api/register', {{method: 'POST', headers: {{'Content-Type': 'application/json', 'X-Client-Id': getCid()}}, body: JSON.stringify({{name: name, email: email, password: pass}})}});
        const d = await r.json();
        if (d.ok) {{ setAuthed(true, d.name); close(); toast('注册成功，已自动登录。'); }}
        else setNote('auth-note-register', d.msg || '注册失败，请稍后重试。');
      }} catch (err) {{ setNote('auth-note-register', '网络异常，请稍后重试。'); }}
      busy(btn, false);
    }}
    async function submitLogin() {{
      const email = (document.getElementById('auth-login-email') || {{}}).value || '';
      const pass = (document.getElementById('auth-login-pass') || {{}}).value || '';
      if (!email || !pass) {{ setNote('auth-note-login', '请填写邮箱和密码。'); return; }}
      const btn = document.getElementById('auth-submit-login');
      busy(btn, true);
      try {{
        const r = await fetch(API + '/api/login', {{method: 'POST', headers: {{'Content-Type': 'application/json', 'X-Client-Id': getCid()}}, body: JSON.stringify({{email: email, password: pass}})}});
        const d = await r.json();
        if (d.ok) {{ setAuthed(true, d.name); close(); toast('登录成功。'); }}
        else setNote('auth-note-login', d.msg || '登录失败，请稍后重试。');
      }} catch (err) {{ setNote('auth-note-login', '网络异常，请稍后重试。'); }}
      busy(btn, false);
    }}
    tabs.forEach(t => t.onclick = () => switchTab(t.dataset.tab));
    const closeBtn = document.getElementById('auth-close');
    if (closeBtn) closeBtn.onclick = close;
    overlay.addEventListener('click', e => {{ if (e.target === overlay) close(); }});
    document.addEventListener('keydown', e => {{ if (e.key === 'Escape') close(); }});
    const sr = document.getElementById('auth-submit-register');
    const sl = document.getElementById('auth-submit-login');
    if (sr) sr.onclick = submitRegister;
    if (sl) sl.onclick = submitLogin;
    return {{open: open, close: close}};
  }})();

  // 页头注册/登录入口
  document.addEventListener('click', function(e) {{
    const b = e.target.closest ? e.target.closest('.auth-entry') : null;
    if (b && auth) {{
      e.preventDefault();
      if (b.id === 'auth-login' && isAuthed()) {{
        try {{ fetch(API + '/api/logout?cid=' + getCid()); }} catch (e) {{}}
        setAuthed(false);
        toast('已退出登录。');
        return;
      }}
      auth.open(b.id === 'auth-login' ? 'login' : 'register');
    }}
  }});

  // 文件名点击：未登录不可进入详情（站内底层页）
  document.addEventListener('click', function(e) {{
    const a = e.target.closest ? e.target.closest('a.track-name') : null;
    if (a) {{
      if (!isAuthed()) {{
        e.preventDefault();
        if (auth) {{
          auth.open('login');
          const note = document.getElementById('auth-note-login');
          if (note) note.textContent = '登录后即可查看曲目详情与完整播放。';
        }}
        toast('登录后可查看曲目详情。');
      }} else {{
        e.preventDefault();
        setQuery({{id: a.dataset.id}});
        route();
        window.scrollTo({{top: 0, behavior: 'smooth'}});
      }}
    }}
  }});

  // 试听按钮事件委托（覆盖 JS 渲染行与首页预渲染行）
  document.addEventListener('click', function(e) {{
    const btn = e.target.closest ? e.target.closest('.act-listen') : null;
    if (btn) {{
      e.preventDefault();
      player.show(btn.dataset.id, btn.dataset.name, btn.dataset.au);
    }}
  }});

  // 下载按钮：未登录拦截
  document.addEventListener('click', function(e) {{
    const a = e.target.closest ? e.target.closest('a.act-download') : null;
    if (a && !isAuthed()) {{
      e.preventDefault();
      if (auth) auth.open('login');
      toast('登录后可下载曲目。');
    }}
  }});

  // ── 初始化 ──
  window.addEventListener('DOMContentLoaded', async () => {{
    setupSearch();
    refreshAuthUI();
    // 校验后台会话（服务重启后自动登出）
    fetch(API + '/api/session?cid=' + getCid()).then(r => r.json()).then(d => {{ setAuthed(!!d.ok, d.name); }}).catch(() => {{}});
    const ok = await loadData();
    if (ok) {{
      route();
      window.addEventListener('popstate', route);
    }}
  }});
}})();
"""


def generate_html(stats, latest_tracks):
    """生成 index.html，首页最新曲目内嵌以加快首屏。"""
    latest_rows = ""
    for t in latest_tracks:
        fmt_cls = "tag-mashup" if t.get("format") == "mashup" else "tag-single"
        fmt_name = "串烧" if t.get("format") == "mashup" else "单曲"
        lang_map = {"zh": ("tag-zh", "中文"), "en": ("tag-en", "英文"), "other": ("tag-other", "其他")}
        lang_cls, lang_name = lang_map.get(t.get("language"), ("tag-other", "其他"))
        size_str = f'{t["size_mib"]} MiB' if t.get("size_mib") is not None else "-"
        name_attr = html.escape(t['filename'], quote=True)
        au_attr = html.escape(t.get("audio_url") or "", quote=True)
        latest_rows += f"""                <tr>
                    <td class="col-id">{t['id']}</td>
                    <td><a href="?id={t['id']}" class="track-name">{t['filename']}</a></td>
                    <td class="col-size">{size_str}</td>
                    <td class="col-time">{t.get('time','')}</td>
                    <td class="col-tags"><span class="tag {fmt_cls}">{fmt_name}</span><span class="tag {lang_cls}">{lang_name}</span></td>
                    <td class="col-actions"><button type="button" class="act-btn act-listen" data-id="{t['id']}" data-name="{name_attr}" data-au="{au_attr}">试听</button><a href="javascript:;" onclick="location.href=(window.API_BASE||'')+'/api/download/{t['id']}?cid='+getCid()" download="{name_attr}" class="act-btn act-download">下载</a></td>
                </tr>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>9GDJ DJ 索引 — 单曲 / 串烧 / 中英文分类</title>
    <meta name="description" content="互联网公开曲目元数据索引站，按单曲/串烧、中文/英文分类，支持搜索和日期归档。仅元数据索引，不存储音频文件。">
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <script>window.API_BASE = '';</script>
    <header>
        <div class="header-inner">
            <div class="logo">🎧 9GDJ Index <span>曲目元数据索引</span></div>
            <nav>
                <a href="?" id="nav-home">首页</a>
                <a href="?view=all" id="nav-all">全部曲目</a>
                <a href="?view=dates" id="nav-dates">日期归档</a>
                <a href="?format=single">单曲</a>
                <a href="?format=mashup">串烧</a>
            </nav>
            <nav style="gap:2px;">
                <span class="auth-entry" style="color:#7cf59c;font-weight:600;" id="auth-auto">🔓 自动授权已开启</span>
            </nav>
            <div class="search-box">
                <input type="text" id="search-input" placeholder="搜索曲目名...">
                <button id="search-btn">搜索</button>
            </div>
        </div>
    </header>
    <main id="main">
        <div class="loading"><div class="spinner"></div>正在加载曲目数据...</div>
    </main>
    <footer>
        <p>数据来源：互联网 公开列表 | 仅元数据索引，不存储音频文件 | 共 {stats['total']:,} 首曲目</p>
        <p>打开即可试听、下载（系统自动授权，无需注册登录）</p>
        <p>生成时间：{stats.get('generated_at', '')[:19].replace('T', ' ')} | 分类阈值：≥{stats.get('size_threshold_mib', 100)} MiB 即为串烧</p>
    </footer>
    <script src="assets/app.js"></script>
</body>
</html>
"""


def main():
    print("加载分类数据...")
    tracks, stats = load_data()
    print(f"  {len(tracks)} 条曲目")

    # 清理并创建站点目录
    if os.path.exists(SITE_DIR):
        shutil.rmtree(SITE_DIR)
    os.makedirs(os.path.join(SITE_DIR, "assets"), exist_ok=True)
    os.makedirs(os.path.join(SITE_DIR, "data"), exist_ok=True)

    # 1. 精简曲目数据
    print("生成精简曲目数据...")
    minimal = build_minimal_tracks(tracks)
    with open(os.path.join(SITE_DIR, "data", "tracks.json"), "w", encoding="utf-8") as f:
        json.dump(minimal, f, ensure_ascii=False, separators=(",", ":"))
    tracks_size = os.path.getsize(os.path.join(SITE_DIR, "data", "tracks.json"))
    print(f"  tracks.json: {tracks_size / 1024 / 1024:.1f} MB")

    # 2. 统计数据
    with open(os.path.join(SITE_DIR, "data", "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, separators=(",", ":"))

    # 3. 日期列表
    dates = build_dates_list(tracks)
    with open(os.path.join(SITE_DIR, "data", "dates.json"), "w", encoding="utf-8") as f:
        json.dump(dates, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  日期归档: {len(dates)} 天")

    # 4. CSS
    with open(os.path.join(SITE_DIR, "assets", "style.css"), "w", encoding="utf-8") as f:
        f.write(generate_css())

    # 5. JS
    with open(os.path.join(SITE_DIR, "assets", "app.js"), "w", encoding="utf-8") as f:
        f.write(generate_js(len(tracks), PAGE_SIZE, LATEST_ON_HOME))

    # 6. HTML
    latest = tracks[:LATEST_ON_HOME]
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(generate_html(stats, latest))

    print(f"\n站点已生成到: {SITE_DIR}")
    print(f"  index.html")
    print(f"  assets/style.css")
    print(f"  assets/app.js")
    print(f"  data/tracks.json ({tracks_size / 1024 / 1024:.1f} MB)")
    print(f"  data/stats.json")
    print(f"  data/dates.json")


if __name__ == "__main__":
    main()
