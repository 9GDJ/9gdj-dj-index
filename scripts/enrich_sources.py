#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
来源站音频地址补充：抓取每条曲目的来源播放页，提取直连音频 URL。

覆盖来源:
  - djuu.com        -> music = {... file: 'X' ...}  => https://mp4.djuu.com/{X}.m4a
  - 172mix.com      -> 页面内联脚本 jPlayer src: "https://mp3.172mix.com/mp3/....m4a"

产出: 写入 data/audio_map.json（{id: 直连音频URL} 侧车文件，原子写入）。
      raw_tracks.json / classified.json 均不被本脚本修改，scrape/classify 重跑不会丢失已提取结果。
断点续跑: 进度存 data/enrich_state.json；只处理尚未提取的记录。
用法: python scripts/enrich_sources.py [--limit N] [--max-workers 4]
"""

import json
import os
import random
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
RAW_JSON = os.path.join(DATA_DIR, "raw_tracks.json")
STATE_JSON = os.path.join(DATA_DIR, "enrich_state.json")
AUDIO_MAP_JSON = os.path.join(DATA_DIR, "audio_map.json")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

DJUU_FILE_RE = re.compile(r"music\s*=\s*\{[^}]*?file\s*:\s*'([^']+)'", re.S)
DJUU_AUDIO = "https://mp4.djuu.com/{}.m4a"
MIX_AUDIO_RE = re.compile(r"https://mp3\.172mix\.com/[^\"'\s<>]+\.(?:m4a|mp3)", re.I)

session_local = threading.local()


def get_session():
    if not hasattr(session_local, "s"):
        session_local.s = requests.Session()
        session_local.s.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    return session_local.s


def extract_audio(url, filename):
    """根据来源 URL 抓取播放页并提取直连音频地址，返回 URL 或 None。"""
    host = url.split("://")[1].split("/")[0] if "://" in url else url.split("/")[0]
    try:
        s = get_session()
        resp = s.get(url, timeout=20)
        resp.raise_for_status()
        html = resp.text
    except Exception:
        return None

    if "djuu.com" in host:
        m = DJUU_FILE_RE.search(html)
        if m:
            return DJUU_AUDIO.format(m.group(1))
    elif "172mix.com" in host:
        m = MIX_AUDIO_RE.search(html)
        if m:
            return m.group(0)
    return None


def main():
    args = sys.argv[1:]
    limit = None
    workers = 4
    i = 0
    while i < len(args):
        if args[i] == "--limit":
            limit = int(args[i + 1]); i += 2
        elif args[i] == "--max-workers":
            workers = int(args[i + 1]); i += 2
        else:
            i += 1

    with open(RAW_JSON, "r", encoding="utf-8") as f:
        tracks = json.load(f)
    print(f"总记录: {len(tracks)}")

    audio_map = {}
    if os.path.exists(AUDIO_MAP_JSON):
        with open(AUDIO_MAP_JSON, "r", encoding="utf-8") as f:
            audio_map = json.load(f)
    print(f"已有直连地址: {len(audio_map)}")

    state = {}
    if os.path.exists(STATE_JSON):
        with open(STATE_JSON, "r", encoding="utf-8") as f:
            state = json.load(f)
    done_ids = set(state.get("done", []))
    print(f"已完成: {len(done_ids)}")

    todo = [(i, t) for i, t in enumerate(tracks) if t.get("id") not in done_ids and (t.get("source_url") or "")]
    if limit:
        todo = todo[:limit]
    print(f"待处理: {len(todo)}")

    lock = threading.Lock()
    ok = skip = 0
    t0 = time.time()

    def work(item):
        idx, t = item
        au = extract_audio(t["source_url"], t.get("filename", ""))
        return idx, t, au

    def save_state():
        with open(STATE_JSON + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"done": list(done_ids)}, f)
        os.replace(STATE_JSON + ".tmp", STATE_JSON)

    def save_map():
        with open(AUDIO_MAP_JSON + ".tmp", "w", encoding="utf-8") as f:
            json.dump(audio_map, f, ensure_ascii=False)
        os.replace(AUDIO_MAP_JSON + ".tmp", AUDIO_MAP_JSON)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(work, item) for item in todo]
        for k, fut in enumerate(as_completed(futs)):
            idx, t, au = fut.result()
            with lock:
                if au:
                    audio_map[str(t["id"])] = au
                    ok += 1
                else:
                    skip += 1
                done_ids.add(t["id"])
            if (k + 1) % 25 == 0:
                with lock:
                    print(f"  进度 {k+1}/{len(todo)}  成功={ok} 跳过={skip}  用时 {time.time()-t0:.0f}s")
                    save_state()
                    save_map()
            time.sleep(random.uniform(0.3, 0.8))

    save_state()
    save_map()

    print(f"\n完成: 成功={ok} 失败/跳过={skip}  累计直连地址={len(audio_map)}/{len(tracks)}  用时 {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
