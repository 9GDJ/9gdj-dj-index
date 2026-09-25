#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pandadj.com 公开列表页爬虫（仅元数据，不下载任何音频文件）。

用法:
    python scrape.py                  # 全量抓取，自动断点续抓
    python scrape.py --pages 1-3      # 只抓第 1-3 页（测试用）
    python scrape.py --max-workers 3  # 调整并发数

输出:
    data/raw_tracks.csv   — 全量曲目元数据（UTF-8, 含 BOM 以便 Excel 打开）
    data/raw_tracks.json  — 同上的 JSON 数组
    data/scrape_state.json — 断点状态（已完成页码、失败页码）
"""

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ── 配置 ──────────────────────────────────────────────
BASE_URL = "https://pandadj.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
MAX_RETRIES = 4
TIMEOUT = 20
DELAY_MIN = 0.3
DELAY_MAX = 0.9

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "raw_tracks.csv")
JSON_PATH = os.path.join(DATA_DIR, "raw_tracks.json")
STATE_PATH = os.path.join(DATA_DIR, "scrape_state.json")

CSV_FIELDS = ["id", "source_url", "filename", "size_mib", "time"]


# ── 工具函数 ──────────────────────────────────────────
def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_pages": [], "failed_pages": [], "total_pages": None}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def parse_size(text):
    """'14.47 MiB' -> 14.47; 无法解析返回 None。"""
    if not text:
        return None
    m = re.search(r"([\d.]+)", text.strip())
    return float(m.group(1)) if m else None


def parse_page(html):
    """解析一页 HTML，返回 (tracks_list, max_page_or_None)。"""
    soup = BeautifulSoup(html, "lxml")
    tracks = []

    # 数据表体中的行：排除 class="collapse" 的音频展开行
    tbody = soup.find("tbody")
    if tbody is None:
        return tracks, None

    for tr in tbody.find_all("tr", recursive=False):
        if tr.get("class") and "collapse" in tr.get("class", []):
            continue
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 6:
            continue

        # td[0] ID
        id_text = tds[0].get_text(strip=True)
        try:
            track_id = int(id_text)
        except (ValueError, TypeError):
            continue

        # td[1] 来源 URL
        source_url = tds[1].get_text(strip=True)

        # td[2] 文件名（在 <a> 内的 span 中）
        filename = ""
        a_tag = tds[2].find("a")
        if a_tag:
            filename = a_tag.get_text(strip=True)
        else:
            filename = tds[2].get_text(strip=True)

        # td[4] 大小（td[3] 是按钮列）
        size_text = tds[4].get_text(strip=True) if len(tds) > 4 else ""
        size_mib = parse_size(size_text)

        # td[5] 时间
        time_text = tds[5].get_text(strip=True) if len(tds) > 5 else ""

        tracks.append({
            "id": track_id,
            "source_url": source_url,
            "filename": filename,
            "size_mib": size_mib,
            "time": time_text,
        })

    # 解析分页：找最大页码
    max_page = None
    pagination = soup.find("ul", class_="pagination")
    if pagination:
        page_nums = []
        for a in pagination.find_all("a"):
            href = a.get("href", "")
            m = re.search(r"[?&]page=(\d+)", href)
            if m:
                page_nums.append(int(m.group(1)))
        # 也检查 span（当前页/禁用页）
        for span in pagination.find_all("span"):
            txt = span.get_text(strip=True)
            if txt.isdigit():
                page_nums.append(int(txt))
        if page_nums:
            max_page = max(page_nums)

    return tracks, max_page


def fetch_page(session, page_num):
    """抓取单页，带重试。返回 (tracks, max_page) 或抛出异常。"""
    url = f"{BASE_URL}?page={page_num}" if page_num > 1 else BASE_URL
    last_exc = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            resp = session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=False)

            # 302 可能是限流
            if resp.status_code == 302:
                wait = 2 ** attempt + random.uniform(0, 1)
                print(f"  [page {page_num}] 302 redirect, retry {attempt}/{MAX_RETRIES}, wait {wait:.1f}s")
                time.sleep(wait)
                continue
            if resp.status_code == 429:
                wait = 3 ** attempt + random.uniform(0, 2)
                print(f"  [page {page_num}] 429 rate-limited, retry {attempt}/{MAX_RETRIES}, wait {wait:.1f}s")
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = 2 ** attempt
                print(f"  [page {page_num}] {resp.status_code}, retry {attempt}/{MAX_RETRIES}, wait {wait:.1f}s")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            tracks, max_page = parse_page(resp.text)
            return tracks, max_page

        except requests.RequestException as e:
            last_exc = e
            wait = 2 ** attempt + random.uniform(0, 1)
            print(f"  [page {page_num}] request error: {e}, retry {attempt}/{MAX_RETRIES}, wait {wait:.1f}s")
            time.sleep(wait)

    raise RuntimeError(f"page {page_num} failed after {MAX_RETRIES} retries: {last_exc}")


def detect_total_pages(session):
    """抓第一页，从分页器推断总页数。"""
    print("检测总页数...")
    tracks, max_page = fetch_page(session, 1)
    if max_page is None:
        # 兜底：逐页探测直到空页
        print("  分页器未找到页码，使用逐页探测...")
        probe = 100
        while True:
            t, _ = fetch_page(session, probe)
            if len(t) == 0:
                # 二分查找
                lo, hi = probe // 2, probe
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    t, _ = fetch_page(session, mid)
                    if len(t) > 0:
                        lo = mid
                    else:
                        hi = mid - 1
                max_page = lo
                break
            probe *= 2
    print(f"  总页数: {max_page}")
    return max_page, tracks


def append_csv(tracks):
    """增量写入 CSV（如果文件不存在则写表头）。"""
    file_exists = os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0
    with open(CSV_PATH, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        for t in tracks:
            writer.writerow(t)


def deduplicate_csv():
    """按 id 去重 CSV，保持首次出现顺序。"""
    if not os.path.exists(CSV_PATH):
        return 0
    seen = set()
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row.get("id", "")
            if rid and rid not in seen:
                seen.add(rid)
                rows.append(row)
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def csv_to_json():
    """将最终 CSV 转为 JSON。"""
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # size_mib 转回 float
            try:
                row["size_mib"] = float(row["size_mib"]) if row["size_mib"] else None
            except (ValueError, TypeError):
                row["size_mib"] = None
            try:
                row["id"] = int(row["id"])
            except (ValueError, TypeError):
                pass
            rows.append(row)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="pandadj.com 列表爬虫")
    parser.add_argument("--pages", type=str, default=None,
                        help="只抓指定页码范围，如 1-3 或 5（测试用）")
    parser.add_argument("--max-workers", type=int, default=5)
    parser.add_argument("--reset", action="store_true",
                        help="清空已有数据和状态，重新开始")
    args = parser.parse_args()

    ensure_dirs()

    if args.reset:
        for p in [CSV_PATH, JSON_PATH, STATE_PATH]:
            if os.path.exists(p):
                os.remove(p)
        print("已重置状态和数据文件。")

    state = load_state()
    session = requests.Session()

    # 确定要抓的页码
    if args.pages:
        if "-" in args.pages:
            lo, hi = map(int, args.pages.split("-"))
            pages_to_fetch = list(range(lo, hi + 1))
        else:
            pages_to_fetch = [int(args.pages)]
        total_pages = max(pages_to_fetch)
    else:
        total_pages, first_page_tracks = detect_total_pages(session)
        state["total_pages"] = total_pages
        save_state(state)
        # 第一页已经抓了，直接写入
        if first_page_tracks:
            append_csv(first_page_tracks)
            state["completed_pages"].append(1)
            save_state(state)
            print(f"  第 1 页: {len(first_page_tracks)} 条")
        pages_to_fetch = [p for p in range(2, total_pages + 1)
                          if p not in state["completed_pages"]]

    print(f"\n开始抓取 {len(pages_to_fetch)} 页 (并发 {args.max_workers})...")
    start_time = time.time()
    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_page = {
            executor.submit(fetch_page, session, p): p
            for p in pages_to_fetch
        }
        for future in as_completed(future_to_page):
            page = future_to_page[future]
            try:
                tracks, _ = future.result()
                if tracks:
                    append_csv(tracks)
                state["completed_pages"].append(page)
                success_count += 1
                if success_count % 20 == 0 or success_count == len(pages_to_fetch):
                    elapsed = time.time() - start_time
                    rate = success_count / elapsed if elapsed > 0 else 0
                    eta = (len(pages_to_fetch) - success_count) / rate if rate > 0 else 0
                    print(f"  进度: {success_count}/{len(pages_to_fetch)} 页 "
                          f"({rate:.1f}页/s, ETA {eta/60:.1f}min)")
                if success_count % 100 == 0:
                    save_state(state)
            except Exception as e:
                print(f"  [page {page}] 最终失败: {e}")
                state["failed_pages"].append(page)
                fail_count += 1

    save_state(state)
    elapsed = time.time() - start_time
    print(f"\n抓取完成: 成功 {success_count} 页, 失败 {fail_count} 页, 耗时 {elapsed/60:.1f} 分钟")

    # 重试失败页（串行，更保守）
    if state["failed_pages"]:
        print(f"\n重试 {len(state['failed_pages'])} 个失败页（串行）...")
        still_failed = []
        for page in state["failed_pages"]:
            try:
                tracks, _ = fetch_page(session, page)
                if tracks:
                    append_csv(tracks)
                state["completed_pages"].append(page)
                print(f"  page {page}: 重试成功 ({len(tracks)} 条)")
            except Exception as e:
                still_failed.append(page)
                print(f"  page {page}: 仍失败: {e}")
        state["failed_pages"] = still_failed
        save_state(state)

    # 去重 & 转 JSON
    print("\n去重并生成 JSON...")
    unique_count = deduplicate_csv()
    json_count = csv_to_json()
    print(f"  CSV 去重后: {unique_count} 条")
    print(f"  JSON 记录: {json_count} 条")

    # 覆盖率报告
    completed = len(set(state["completed_pages"]))
    total = state.get("total_pages") or total_pages
    print(f"\n=== 抓取报告 ===")
    print(f"  总页数: {total}")
    print(f"  已完成页: {completed} ({completed/total*100:.1f}%)")
    print(f"  失败页: {state['failed_pages']}")
    print(f"  去重后曲目数: {unique_count}")
    print(f"  CSV: {CSV_PATH}")
    print(f"  JSON: {JSON_PATH}")


if __name__ == "__main__":
    main()
