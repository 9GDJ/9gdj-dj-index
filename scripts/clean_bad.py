# -*- coding: utf-8 -*-
"""清洗：删除 filename='-' 或 size_mib 缺失/0 的项目（原子写）"""
import json, io, os, tempfile, time

BASE = r'C:\Users\Administrator\DoubaoWork\chats\2026-09-23\new-chat-1\panda-index-site\data'
P = BASE + r'\classified.json'

with io.open(P, 'r', encoding='utf-8') as f:
    tracks = json.load(f)

bad_ids = set()
for t in tracks:
    if (t.get('filename') or '').strip() == '-' or not (t.get('size_mib') or 0):
        bad_ids.add(t.get('id'))
print('to remove:', len(bad_ids))

clean = [t for t in tracks if t.get('id') not in bad_ids]
print('remaining:', len(clean))

# 原子写
fd, tmp = tempfile.mkstemp(dir=BASE, suffix='.tmp')
with io.open(tmp, 'w', encoding='utf-8') as f:
    json.dump(clean, f, ensure_ascii=False)
os.close(fd)
os.replace(tmp, P)
print('classified.json rewritten:', os.path.getsize(P))

# 同步 audio_map.json 清理
AM = BASE + r'\audio_map.json'
if os.path.exists(AM):
    with io.open(AM, 'r', encoding='utf-8') as f:
        am = json.load(f)
    before = len(am)
    am = {k: v for k, v in am.items() if int(k) not in bad_ids}
    fd, tmp = tempfile.mkstemp(dir=BASE, suffix='.tmp')
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(am, f, ensure_ascii=False)
    os.close(fd)
    os.replace(tmp, AM)
    print('audio_map: %d -> %d' % (before, len(am)))

# ── 重算 stats.json（清洗后统计口径必须刷新）──
from collections import Counter
SP = BASE + r'\stats.json'
if os.path.exists(SP):
    with io.open(SP, 'r', encoding='utf-8') as f:
        old = json.load(f)
else:
    old = {}
fmt = Counter(t.get('format') for t in clean)
lang = Counter(t.get('language') for t in clean)
combo = Counter((t.get('format'), t.get('language')) for t in clean)
dc = Counter(t.get('date') for t in clean if t.get('date'))
today = old.get('today', '')
stats = {
    'total': len(clean),
    'format': {'single': fmt.get('single', 0), 'mashup': fmt.get('mashup', 0)},
    'language': {'zh': lang.get('zh', 0), 'en': lang.get('en', 0), 'other': lang.get('other', 0)},
    'combo': {
        'zh_single': combo.get(('single', 'zh'), 0),
        'other_single': combo.get(('single', 'other'), 0),
        'zh_mashup': combo.get(('mashup', 'zh'), 0),
        'en_single': combo.get(('single', 'en'), 0),
        'en_mashup': combo.get(('mashup', 'en'), 0),
    },
    'today': today,
    'today_count': dc.get(today, 0),
    'date_count': len(dc),
    'latest_date': max(dc) if dc else '',
    'earliest_date': min(dc) if dc else '',
    'top_dates': sorted(dc.items(), key=lambda x: (-x[1], x[0]))[:30],
    'size_threshold_mib': old.get('size_threshold_mib', 20.0),
    'mashup_keywords': old.get('mashup_keywords', ['串烧', 'mashup', 'mixset', '连续串', '大串烧', '串烧版']),
    'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
}
fd, tmp = tempfile.mkstemp(dir=BASE, suffix='.tmp')
with io.open(tmp, 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, separators=(',', ':'))
os.close(fd)
os.replace(tmp, SP)
print('stats refreshed: total=%d single=%d mashup=%d today=%s' % (stats['total'], stats['format']['single'], stats['format']['mashup'], stats['today_count']))
