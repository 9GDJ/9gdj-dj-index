#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分类脚本：读取 raw_tracks.json，为每条曲目打上分类标签并输出统计。

分类规则（可在 CONFIG 中调整）：
  - 单曲/串烧：size_mib >= MASHUP_SIZE_THRESHOLD(100 MiB) 或文件名含「串烧」关键词 → 串烧；否则单曲
  - 中文/英文：文件名含中文字符 → 中文；否则含拉丁字母 → 英文；均无 → 其他
  - 日期：从 time 字段提取 YYYY-MM-DD

输出:
  data/classified.json   — 带分类标签的全量数据
  data/stats.json        — 统计数字（总数、分类计数、日期分布等）
  data/size_histogram.json — 文件大小直方图（用于阈值验证）
"""

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime

# ── 可配置分类规则 ────────────────────────────────────
MASHUP_SIZE_THRESHOLD = 100.0  # MiB，大于等于此值视为串烧（按用户要求调整）
MASHUP_KEYWORDS = ["串烧", "mashup", "mash up", "mixset", "megamix", "连续串", "大串烧", "串烧版", "连续播放"]

CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z]")
# 括号及其中内容（DJ 混音注释/提供者标注），用于剥离出歌手/歌名主体
PAREN_PAIR = re.compile(r"[(\(（\[【][^\)）\]】]*[\)）\]】]")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
RAW_JSON = os.path.join(DATA_DIR, "raw_tracks.json")
CLASSIFIED_JSON = os.path.join(DATA_DIR, "classified.json")
STATS_JSON = os.path.join(DATA_DIR, "stats.json")
HISTOGRAM_JSON = os.path.join(DATA_DIR, "size_histogram.json")


def classify_format(filename, size_mib):
    """返回 'mashup' 或 'single'。仅按大小判定：size >= 阈值(100 MiB) → 串烧；否则单曲（用户定稿规则）。"""
    if size_mib is not None and size_mib >= MASHUP_SIZE_THRESHOLD:
        return "mashup"
    return "single"

def classify_language(filename):
    """精准判定歌曲主体语言：先剥离括号内 DJ 混音/提供者注释，再对歌手/歌名主体判 zh/en/other。"""
    base = filename.rsplit(".", 1)[0] if "." in filename else filename
    core = PAREN_PAIR.sub("", base).strip()
    if not core:
        # 主体被括号完全占据（罕见），退回全名判定
        core = base
    if CHINESE_RE.search(core):
        return "zh"
    if LATIN_RE.search(core):
        return "en"
    return "other"


def extract_date(time_str):
    """从 '2026-09-23 10:19' 提取 '2026-09-23'，失败返回 None。"""
    if not time_str:
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", time_str.strip())
    return m.group(1) if m else None


def build_size_histogram(tracks):
    """构建文件大小分布直方图（MiB）。"""
    bins = [0, 5, 10, 15, 20, 30, 50, 80, 120, 200, 500, float("inf")]
    labels = ["0-5", "5-10", "10-15", "15-20", "20-30", "30-50",
              "50-80", "80-120", "120-200", "200-500", "500+"]
    counts = [0] * len(labels)
    no_size = 0
    for t in tracks:
        s = t.get("size_mib")
        if s is None:
            no_size += 1
            continue
        for i in range(len(bins) - 1):
            if bins[i] <= s < bins[i + 1]:
                counts[i] += 1
                break
    return {
        "bins_mib": labels,
        "counts": counts,
        "no_size": no_size,
        "threshold_used": MASHUP_SIZE_THRESHOLD,
    }


def main():
    if not os.path.exists(RAW_JSON):
        print(f"错误: 找不到 {RAW_JSON}，请先运行 scrape.py")
        return

    with open(RAW_JSON, "r", encoding="utf-8") as f:
        tracks = json.load(f)

    print(f"读取 {len(tracks)} 条原始记录")

    # 分类
    format_counter = Counter()
    lang_counter = Counter()
    combo_counter = Counter()
    date_counter = Counter()
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_count = 0

    for t in tracks:
        fmt = classify_format(t["filename"], t.get("size_mib"))
        lang = classify_language(t["filename"])
        date = extract_date(t.get("time", ""))

        t["format"] = fmt        # single / mashup
        t["language"] = lang     # zh / en / other
        t["date"] = date         # YYYY-MM-DD or None

        format_counter[fmt] += 1
        lang_counter[lang] += 1
        combo_counter[f"{lang}_{fmt}"] += 1
        if date:
            date_counter[date] += 1
            if date == today_str:
                today_count += 1

    # 按 ID 降序排列（最新入库在前）
    tracks.sort(key=lambda x: x.get("id", 0), reverse=True)

    # 写分类数据
    with open(CLASSIFIED_JSON, "w", encoding="utf-8") as f:
        json.dump(tracks, f, ensure_ascii=False)

    # 直方图
    histogram = build_size_histogram(tracks)
    with open(HISTOGRAM_JSON, "w", encoding="utf-8") as f:
        json.dump(histogram, f, ensure_ascii=False, indent=2)

    # 统计
    sorted_dates = sorted(date_counter.items(), key=lambda x: x[0], reverse=True)
    stats = {
        "total": len(tracks),
        "format": dict(format_counter),
        "language": dict(lang_counter),
        "combo": dict(combo_counter),
        "today": today_str,
        "today_count": today_count,
        "date_count": len(date_counter),
        "latest_date": sorted_dates[0][0] if sorted_dates else None,
        "earliest_date": sorted_dates[-1][0] if sorted_dates else None,
        "top_dates": sorted_dates[:30],
        "size_threshold_mib": MASHUP_SIZE_THRESHOLD,
        "mashup_keywords": MASHUP_KEYWORDS,
        "generated_at": datetime.now().isoformat(),
    }
    with open(STATS_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # 打印报告
    print(f"\n=== 分类报告 ===")
    print(f"总数: {len(tracks)}")
    print(f"单曲: {format_counter.get('single', 0)}, 串烧: {format_counter.get('mashup', 0)}")
    print(f"中文: {lang_counter.get('zh', 0)}, 英文: {lang_counter.get('en', 0)}, 其他: {lang_counter.get('other', 0)}")
    print(f"组合: {dict(combo_counter)}")
    print(f"今日({today_str})新增: {today_count}")
    print(f"日期范围: {stats['earliest_date']} ~ {stats['latest_date']} ({len(date_counter)} 天)")
    print(f"\n大小分布:")
    for label, count in zip(histogram["bins_mib"], histogram["counts"]):
        print(f"  {label:>8} MiB: {count}")
    print(f"  无大小数据: {histogram['no_size']}")
    print(f"\n输出: {CLASSIFIED_JSON}")
    print(f"输出: {STATS_JSON}")
    print(f"输出: {HISTOGRAM_JSON}")


if __name__ == "__main__":
    main()
