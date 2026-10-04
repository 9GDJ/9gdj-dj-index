/* ===== 9GDJ DJ 索引 — 客户端逻辑 ===== */
(function() {
  'use strict';

  const PAGE_SIZE = 50;
  let ALL_TRACKS = null;
  const LOCAL_MODE = (window.API_BASE === '');
  let STATS = null;
  let DATES = null;
  let currentPage = 1;
  let filtered = null;

  const FORMAT_NAMES = ['单曲', '串烧'];
  const LANG_NAMES = ['中文', '英文'];

  // ── 工具 ──
  function $(sel) { return document.querySelector(sel); }
  function el(tag, attrs, children) {
    const e = document.createElement(tag);
    if (attrs) for (const k in attrs) {
      if (k === 'class') e.className = attrs[k];
      else if (k === 'text') e.textContent = attrs[k];
      else e.setAttribute(k, attrs[k]);
    }
    if (children) children.forEach(c => e.appendChild(c));
    return e;
  }

  function getQuery() {
    const q = {};
    new URLSearchParams(window.location.search).forEach((v, k) => q[k] = v);
    return q;
  }

  function setQuery(params) {
    const sp = new URLSearchParams();
    for (const k in params) {
      const v = params[k];
      if (v === '' || v === null || v === undefined) continue;
      sp.set(k, v);
    }
    const qs = sp.toString();
    const url = qs ? '?' + qs : window.location.pathname;
    window.history.pushState({}, '', url);
  }

  // 数据文件双通道：优先 API 代理（CF 边缘缓存加速），失败回退相对路径（GitHub Pages 同源）
  function fetchData(path) {
    const urls = [];
    if (!LOCAL_MODE && window.API_BASE) urls.push(window.API_BASE + '/' + path);
    urls.push(path);
    let lastErr = null;
    return new Promise(function (resolve, reject) {
      let i = 0;
      function next() {
        if (i >= urls.length) return reject(lastErr || new Error('数据加载失败'));
        fetch(urls[i++]).then(function (r) {
          if (r.ok) return resolve(r.json());
          lastErr = new Error('HTTP ' + r.status);
          next();
        }).catch(function (e) { lastErr = e; next(); });
      }
      next();
    });
  }

  // ── 数据加载 ──
  async function loadData() {
    // 首屏只加载统计与日期（小文件）；tracks.json 全量数据懒加载（搜索/分类/详情首次需要时）
    try {
      const [s, d] = await Promise.all([
        fetchData('data/stats.json'),
        fetchData('data/dates.json')
      ]);
      STATS = s;
      DATES = d;
      return true;
    } catch (e) {
      showLoading('数据加载失败: ' + e.message);
      return false;
    }
  }

  // 懒加载曲目数据：format/lang 命中分片（tracks-single[-zh|en|other]/mashup.json），否则拉全量（搜索/全部）
  let TRACKS_PROMISE = null;
  const SPLIT_CACHE = {};
  function splitFileName(fmt, lang) {
    if (fmt === 'single' && lang) return 'data/tracks-single-' + lang + '.json';
    if (fmt === 'single') return 'data/tracks-single.json';
    if (fmt === 'mashup') return 'data/tracks-mashup.json';
    return '';
  }
  function ensureTracks(fmt, lang) {
    const file = splitFileName(fmt, lang);
    if (file) {
      if (SPLIT_CACHE[file]) return Promise.resolve(SPLIT_CACHE[file]);
      if (!SPLIT_CACHE['p-' + file]) {
        SPLIT_CACHE['p-' + file] = fetchData(file)
          .then(t => { SPLIT_CACHE[file] = t; return t; })
          .catch(e => { SPLIT_CACHE['p-' + file] = null; throw e; });
      }
      return SPLIT_CACHE['p-' + file];
    }
    if (ALL_TRACKS) return Promise.resolve(ALL_TRACKS);
    if (!TRACKS_PROMISE) {
      TRACKS_PROMISE = fetchData('data/tracks.json')
        .then(t => { ALL_TRACKS = t; return t; })
        .catch(e => { TRACKS_PROMISE = null; throw e; });
    }
    return TRACKS_PROMISE;
  }
  // 最近 30 天轻量数据（列表首屏秒开；翻页越界/搜索/日期再拉全量）
  let RECENT = null;
  let RECENT_PROMISE = null;
  let FORCE_FULL = false;
  function ensureRecent() {
    if (RECENT) return Promise.resolve(RECENT);
    if (!RECENT_PROMISE) {
      RECENT_PROMISE = fetchData('data/tracks-recent.json')
        .then(t => { RECENT = t; return t; })
        .catch(e => { RECENT_PROMISE = null; throw e; });
    }
    return RECENT_PROMISE;
  }

  function findTrackById(id) {
    if (LOCAL_MODE) {
      return fetch(API + '/api/track?id=' + id).then(r => r.json()).then(d => d.ok ? d.track : null).catch(function() { return null; });
    }
    if (ALL_TRACKS) {
      const t = ALL_TRACKS.find(x => String(x.i) === String(id));
      if (t) return Promise.resolve(t);
    }
    if (RECENT) {
      const t = RECENT.find(x => String(x.i) === String(id));
      if (t) return Promise.resolve(t);
    }
    for (const k in SPLIT_CACHE) {
      const t = SPLIT_CACHE[k] && SPLIT_CACHE[k].find ? SPLIT_CACHE[k].find(x => String(x.i) === String(id)) : null;
      if (t) return Promise.resolve(t);
    }
    const lt = window.__LATEST__ || [];
    const t2 = lt.find(x => String(x.i) === String(id));
    if (t2) return Promise.resolve(t2);
    // 详情直达兜底：先加载最近 30 天秒查；查不到再拉全量（带提示，避免白屏等待）
    return ensureRecent().then(function (arr) {
      const t3 = arr.find(x => String(x.i) === String(id));
      if (t3) return t3;
      showLoading('该曲目不在最近 30 天，正在加载全部历史…');
      return ensureTracks().then(function (arr2) {
        return arr2.find(x => String(x.i) === String(id)) || null;
      });
    }).catch(function () {
      return ensureTracks().then(function (arr2) {
        return arr2.find(x => String(x.i) === String(id)) || null;
      });
    });
  }

  function showLoading(msg) {
    const m = $('#main');
    if (!msg) {
      // 无参数：表格骨架屏（列表加载）
      m.innerHTML = '<div class="skeleton-wrap">' +
        Array.from({length: 6}, function () {
          return '<div class="skeleton-row"><div class="sk sk-a"></div><div class="sk sk-b"></div><div class="sk sk-c"></div><div class="sk sk-d"></div><div class="sk sk-b" style="width:70%"></div></div>';
        }).join('') + '</div>';
      return;
    }
    m.innerHTML = '<div class="loading"><div class="spinner"></div>' + msg + '</div>';
  }
  function hideLoading() { $('#main').innerHTML = ''; }

  // ── 渲染曲目表格 ──
  function renderTrackTable(tracks, container, opts) {
    opts = opts || {};
    if (!tracks || tracks.length === 0) {
      container.innerHTML = '<div class="loading">没有找到匹配的曲目</div>';
      return;
    }
    const wrap = el('div', {class: 'track-table-wrap'});
    const table = el('table', {class: 'track-table'});
    const thead = el('thead');
    thead.appendChild(el('tr', null, [
      el('th', {text: '#'}),
      el('th', {text: '文件名'}),
      el('th', {text: '大小'}),
      el('th', {text: '时间'}),
      el('th', {text: '标签'}),
      el('th', {text: '操作'}),
    ]));
    table.appendChild(thead);
    const tbody = el('tbody');
    tracks.forEach(t => {
      const tr = el('tr');
      tr.appendChild(el('td', {class: 'col-id', text: t.i}));
      const nameTd = el('td');
      const nameA = el('a', {
        href: '?id=' + t.i,
        class: 'track-name',
        text: t.n
      });
      nameA.dataset.id = t.i;
      nameTd.appendChild(nameA);
      tr.appendChild(nameTd);
      tr.appendChild(el('td', {class: 'col-size', text: t.s != null ? t.s + ' MiB' : '-'}));
      tr.appendChild(el('td', {class: 'col-time', text: t.t}));
      const tagTd = el('td', {class: 'col-tags'});
      tagTd.appendChild(el('span', {class: 'tag tag-' + (t.f === 1 ? 'mashup' : 'single'), text: FORMAT_NAMES[t.f]}));
      tagTd.appendChild(el('span', {class: 'tag tag-' + (t.l === 0 ? 'zh' : 'en'), text: LANG_NAMES[t.l]}));
      tr.appendChild(tagTd);
      const actTd = el('td', {class: 'col-actions'});
      const dlUrl = buildDlUrl(t);
      const listenBtn = el('button', {type: 'button', class: 'act-btn act-listen', text: '试听'});
      listenBtn.dataset.id = t.i;
      listenBtn.dataset.name = t.n;
      listenBtn.dataset.au = t.au || '';
      actTd.appendChild(listenBtn);
      actTd.appendChild(el('a', {href: dlUrl, class: 'act-btn act-download', text: '下载', download: t.n}));
      tr.appendChild(actTd);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    container.appendChild(wrap);
  }

  // ── 分页 ──
  function renderPagination(total, page, container, onChange) {
    const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
    const pag = el('div', {class: 'pagination'});

    const prev = el('button', {text: '上一页'});
    prev.disabled = page <= 1;
    prev.onclick = () => onChange(page - 1);
    pag.appendChild(prev);

    // 页码逻辑：显示当前页附近
    const pages = [];
    const range = 2;
    for (let p = 1; p <= totalPages; p++) {
      if (p === 1 || p === totalPages || (p >= page - range && p <= page + range)) {
        pages.push(p);
      } else if (pages[pages.length - 1] !== '...') {
        pages.push('...');
      }
    }
    pages.forEach(p => {
      if (p === '...') {
        pag.appendChild(el('span', {class: 'page-info', text: '...'}));
      } else {
        const btn = el('button', {text: p, class: p === page ? 'current' : ''});
        btn.onclick = () => onChange(p);
        pag.appendChild(btn);
      }
    });

    const next = el('button', {text: '下一页'});
    next.disabled = page >= totalPages;
    next.onclick = () => onChange(page + 1);
    pag.appendChild(next);

    pag.appendChild(el('span', {class: 'page-info', text: page + '/' + totalPages + ' 页 · 共 ' + total + ' 条'}));
    container.appendChild(pag);
  }

  // ── 首页 ──
  function renderHome() {
    const m = $('#main');
    m.innerHTML = '';

    // Hero 品牌区（渐变字标 + 标语 + 数字滚动）
    const hero = el('div', {class: 'hero'});
    const hTitle = el('div', {class: 'hero-title'});
    hTitle.appendChild(el('span', {class: 'hero-g', text: '9GDJ'}));
    hTitle.appendChild(el('span', {class: 'hero-sub', text: 'DJ INDEX'}));
    hero.appendChild(hTitle);
    hero.appendChild(el('div', {class: 'hero-slogan', text: '每日更新 · 互联网公开舞曲索引 · 打开即听即下'}));
    const heroNums = el('div', {class: 'hero-nums'});
    const nums = [
      [STATS.total, '曲目总数', '?view=all'],
      [STATS.format.single || 0, '单曲', '?format=single'],
      [STATS.format.mashup || 0, '串烧', '?format=mashup'],
      [STATS.language.zh || 0, '中文', '?lang=zh'],
      [STATS.language.en || 0, '英文', '?lang=en'],
      [STATS.today_count || 0, '今日新增', '?view=dates'],
    ];
    nums.forEach(function (it) {
      const cell = el('a', {href: it[2], class: 'hero-num', title: '点击查看'});
      const nEl = el('div', {class: 'hero-num-val', text: '0'});
      cell.appendChild(nEl);
      cell.appendChild(el('div', {class: 'hero-num-lbl', text: it[1]}));
      heroNums.appendChild(cell);
      const target = it[0] || 0;
      const dur = 900;
      const t0 = performance.now();
      (function tick(now) {
        const p = Math.min(1, (now - t0) / dur);
        const eased = 1 - Math.pow(1 - p, 3);
        nEl.textContent = Math.round(target * eased).toLocaleString();
        if (p < 1) requestAnimationFrame(tick);
      })(t0);
    });
    hero.appendChild(heroNums);
    m.appendChild(hero);

    // 最新入库（tracks 未加载时用页面内嵌 __LATEST__，首屏秒开）
    m.appendChild(el('div', {class: 'section-title', text: '最新入库'}));
    const latest = (ALL_TRACKS || window.__LATEST__ || []).slice(0, 30);
    renderTrackTable(latest, m);
    const moreLink = el('div', {style: 'text-align:center;margin-top:16px;'});
    moreLink.appendChild(el('a', {href: '?view=all', text: '查看全部 →'}));
    m.appendChild(moreLink);

    // 日期归档入口
    m.appendChild(el('div', {class: 'section-title', text: '按日期归档'}));
    const dateLink = el('div');
    dateLink.appendChild(el('a', {href: '?view=dates', text: '浏览 ' + DATES.length + ' 个入库日期 →'}));
    m.appendChild(dateLink);

    updateNav('home');
  }

  // ── 列表视图（分类/搜索/全部）──
  async function renderList() {
    const q = getQuery();
    const m = $('#main');
    const page = parseInt(q.page) || 1;
    const splitFile = splitFileName(q.format, q.lang);
    // 切换视图时先显示骨架屏（数据就绪后被下方渲染覆盖）
    m.innerHTML = '';
    showLoading();
    // 首屏优先最近 30 天轻量数据（秒开）；搜索/日期/强制全部/翻页越界才拉全量
    let usingRecent = false;
    if (q.q || q.date || FORCE_FULL) {
      if (q.q && !FORCE_FULL) {
        // 搜索优先最近 30 天秒出；近 30 天无命中再自动拉全量（避免历史数据遗漏）
        try {
          await ensureRecent();
          const kw = q.q.toLowerCase();
          const recentHit = RECENT.filter(t => t.n.toLowerCase().includes(kw));
          if (recentHit.length > 0) {
            usingRecent = true;
          } else {
            showLoading('近 30 天未找到，正在搜索全部历史…');
            await ensureTracks(q.format, q.lang);
          }
        } catch (e) {
          await ensureTracks(q.format, q.lang);
        }
      } else {
        await ensureTracks(q.format, q.lang);
      }
    } else {
      try {
        await ensureRecent();
        const recentPages = Math.max(1, Math.ceil(RECENT.length / PAGE_SIZE));
        if (page <= recentPages) {
          usingRecent = true;
        } else {
          await ensureTracks(q.format, q.lang);
        }
      } catch (e) {
        await ensureTracks(q.format, q.lang);
      }
    }
    m.innerHTML = '';

    // 面包屑
    const bc = el('div', {class: 'breadcrumb'});
    bc.appendChild(el('a', {href: '?', text: '首页'}));
    bc.appendChild(el('span', {class: 'sep', text: '/'}));
    let title = '全部曲目';
    if (q.format) title = (q.format === 'mashup' ? '串烧' : '单曲');
    if (q.lang) title = (q.lang === 'zh' ? '中文' : '英文') + title;
    if (q.q) title = '搜索: "' + q.q + '"';
    if (q.date) title = q.date + ' 入库';
    bc.appendChild(el('span', {text: title}));
    m.appendChild(bc);

    // 过滤（recent 首屏数据 / format/lang 分片 / 全量）
    let result = usingRecent ? RECENT : (ALL_TRACKS || SPLIT_CACHE[splitFile] || []);
    if (q.format) result = result.filter(t => (q.format === 'mashup' ? t.f === 1 : t.f === 0));

    if (q.lang) result = result.filter(t => (q.lang === 'zh' ? t.l === 0 : t.l === 1));
    if (q.date) result = result.filter(t => t.d === q.date);
    if (q.q) {
      const kw = q.q.toLowerCase();
      result = result.filter(t => t.n.toLowerCase().includes(kw));
    }
    filtered = result;

    // 修复：recent 首屏数据无匹配（如近 30 天无英文串烧入库）时自动加载全量重筛
    if (usingRecent && result.length === 0 && (q.format || q.lang)) {
      try {
        const full = await ensureTracks(q.format, q.lang);
        result = full || [];
        if (q.format) result = result.filter(t => (q.format === 'mashup' ? t.f === 1 : t.f === 0));
        if (q.lang) result = result.filter(t => (q.lang === 'zh' ? t.l === 0 : t.l === 1));
        if (q.date) result = result.filter(t => t.d === q.date);
        if (q.q) {
          const kw = q.q.toLowerCase();
          result = result.filter(t => t.n.toLowerCase().includes(kw));
        }
        usingRecent = false;
        filtered = result;
      } catch (e) { /* 保持空结果 */ }
    }

    // 过滤栏
    const bar = el('div', {class: 'filter-bar'});
    const fmtSel = el('select');
    [['', '全部格式'], ['single', '单曲'], ['mashup', '串烧']].forEach(([v, label]) => {
      const o = el('option', {value: v, text: label});
      if (q.format === v) o.selected = true;
      fmtSel.appendChild(o);
    });
    fmtSel.onchange = () => { const nq = getQuery(); nq.format = fmtSel.value; if(!nq.format) delete nq.format; nq.page=1; setQuery(nq); renderList(); };
    bar.appendChild(fmtSel);

    const langSel = el('select');
    [['', '全部语言'], ['zh', '中文'], ['en', '英文']].forEach(([v, label]) => {
      const o = el('option', {value: v, text: label});
      if (q.lang === v) o.selected = true;
      langSel.appendChild(o);
    });
    langSel.onchange = () => { const nq = getQuery(); nq.lang = langSel.value; if(!nq.lang) delete nq.lang; nq.page=1; setQuery(nq); renderList(); };
    bar.appendChild(langSel);

    bar.appendChild(el('span', {class: 'result-count', text: (usingRecent ? '最近 30 天 · 共 ' : '共 ') + result.length.toLocaleString() + ' 条'}));
    m.appendChild(bar);

    // 最近模式提示条（可一键加载全部历史/搜索全部历史）
    if (usingRecent) {
      const hint = el('div', {class: 'recent-hint'});
      hint.innerHTML = (q.q
        ? '已搜索最近 30 天入库曲目 · <a href="javascript:;" id="load-full">搜索全部历史</a>'
        : '当前显示最近 30 天入库曲目 · <a href="javascript:;" id="load-full">加载全部历史</a>');
      const lf = hint.querySelector('#load-full');
      lf.onclick = function () { FORCE_FULL = true; renderList(); };
      m.appendChild(hint);
    }

    // 分页
    const start = (page - 1) * PAGE_SIZE;
    const pageTracks = result.slice(start, start + PAGE_SIZE);
    renderTrackTable(pageTracks, m);
    renderPagination(result.length, page, m, (p) => {
      const nq = getQuery(); nq.page = p; setQuery(nq); renderList();
      window.scrollTo({top: 0, behavior: 'smooth'});
    });

    updateNav(q.format || q.q || q.date ? 'list' : 'all');
    // 从详情返回时恢复列表滚动位置
    const savedScroll = sessionStorage.getItem('dj_list_scroll');
    if (savedScroll) {
      sessionStorage.removeItem('dj_list_scroll');
      setTimeout(function() { window.scrollTo(0, parseInt(savedScroll) || 0); }, 60);
    }
  }

  // ── 日期归档 ──
  function renderDates() {
    const m = $('#main');
    m.innerHTML = '';
    const bc = el('div', {class: 'breadcrumb'});
    bc.appendChild(el('a', {href: '?', text: '首页'}));
    bc.appendChild(el('span', {class: 'sep', text: '/'}));
    bc.appendChild(el('span', {text: '日期归档'}));
    m.appendChild(bc);
    m.appendChild(el('div', {class: 'section-title', text: '按入库日期浏览 (' + DATES.length + ' 天)'}));
    const grid = el('div', {class: 'date-grid'});
    DATES.forEach(([d, count]) => {
      const item = el('a', {href: '?date=' + d, class: 'date-item'});
      item.appendChild(el('div', {class: 'd', text: d}));
      item.appendChild(el('div', {class: 'c', text: count + ' 首'}));
      grid.appendChild(item);
    });
    m.appendChild(grid);
    updateNav('dates');
  }

  // ── 曲目详情（站内底层页）──
  async function renderDetail(id) {
    const m = $('#main');
    m.innerHTML = '';
    if (!ALL_TRACKS && !(window.__LATEST__ || []).some(x => String(x.i) === String(id))) showLoading('正在加载曲目数据...');
    let t;
    try { t = await findTrackById(id); } catch (e) { showLoading('数据加载失败: ' + e.message); return; }
    if (!t) {
      m.appendChild(el('div', {class: 'loading', text: '未找到该曲目 (ID=' + id + ')'}));
      return;
    }
    const bc = el('div', {class: 'breadcrumb'});
    bc.appendChild(el('a', {href: '?', text: '首页'}));
    bc.appendChild(el('span', {class: 'sep', text: '/'}));
    bc.appendChild(el('span', {text: '曲目详情'}));
    m.appendChild(bc);

    // 浏览器标签页标题跟随曲目（SEO + 定位体验）
    document.title = String(t.n).slice(0, 60) + ' - 9GDJ DJ 索引';

    const wrap = el('div', {class: 'detail-wrap'});
    wrap.appendChild(el('div', {class: 'detail-title', text: t.n}));

    const meta = el('div', {class: 'detail-meta'});
    const fmtName = FORMAT_NAMES[t.f === 1 ? 1 : 0];
    const langName = LANG_NAMES[t.l === 0 ? 0 : 1];
    [['编号', String(t.i)], ['大小', t.s != null ? t.s + ' MiB' : '-'], ['入库时间', t.t || '-'], ['格式', fmtName], ['语言', langName]].forEach(([k, v]) => {
      const cell = el('div', {class: 'm'});
      cell.appendChild(el('div', {class: 'k', text: k}));
      cell.appendChild(el('div', {class: 'v', text: v}));
      meta.appendChild(cell);
    });
    wrap.appendChild(meta);

    const links = el('div', {class: 'detail-links'});
    if (t.u) links.appendChild(el('a', {href: t.u, target: '_blank', rel: 'noopener', text: '来源站页面 ↗'}));
    links.appendChild(el('a', {href: buildDlUrl(t), class: 'track-download', text: '下载', download: t.n}));
    wrap.appendChild(links);

    // 内嵌波纹播放器（播放爬虫抓取的音频直连地址；无直链时回退官方接口）
    wrap.appendChild(detailPlayer.render(t.i, t.n, t.au || ''));
    m.appendChild(wrap);
    updateNav('home');
  }

  // ── 详情页内嵌波纹播放器（独立于底部播放栏）──
  const detailPlayer = (function() {
    const box = el('div', {class: 'detail-player-box'});
    // 左：播放控制 + 时间（仿 dj024 三段式，与底部播放栏同款）
    const left = el('div', {class: 'player-left'});
    const btnPlay = el('button', {type: 'button', class: 'player-toggle', text: '▶', title: '播放 / 暂停'});
    const timeEl = el('div', {class: 'player-time', text: '0:00 / 0:00'});
    left.appendChild(btnPlay);
    left.appendChild(timeEl);
    // 中：曲名/状态 + 五彩波形（蒙层进度）
    const mid = el('div', {class: 'player-mid'});
    const nameEl = el('div', {class: 'player-name', text: ''});
    const statusEl = el('div', {class: 'player-status'});
    const info = el('div', {class: 'player-info'});
    info.appendChild(nameEl);
    info.appendChild(statusEl);
    mid.appendChild(info);
    const canvas = el('canvas', {class: 'player-wave'});
    canvas.width = 460;
    canvas.height = 48;
    const ctx = canvas.getContext('2d');
    mid.appendChild(canvas);
    // 右：音量 + 单曲循环
    const right = el('div', {class: 'player-right'});
    const muteBtn = el('button', {type: 'button', class: 'player-btn', text: '🔊', title: '静音'});
    const loopBtn = el('button', {type: 'button', class: 'player-btn', text: '🔁', title: '单曲循环：关'});
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
    let apiIdx = 0;
    function currentApi() {
      return (window.API_CANDIDATES && window.API_CANDIDATES[apiIdx]) || API;
    }

    function fmt(s) {
      if (!isFinite(s) || s < 0) s = 0;
      return Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
    }

    function draw() {
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);
      const t = performance.now() / 1000;
      const bars = 60;
      const bw = W / bars;
      const playing = !audio.paused && !audio.ended && !failed && audio.readyState > 0;
      for (let i = 0; i < bars; i++) {
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
      }
      const prog = audio.duration > 0 ? Math.min(1, audio.currentTime / audio.duration) : 0;
      if (prog < 1) {
        ctx.fillStyle = 'rgba(8,12,24,0.55)';
        ctx.fillRect(prog * W, 0, W * (1 - prog), H);
      }
      if (prog > 0) {
        ctx.fillStyle = 'rgba(255,255,255,0.85)';
        ctx.fillRect(prog * W - 1.5, 0, 3, H);
      }
      animId = requestAnimationFrame(draw);
    }

    function stopAnim() {
      if (animId) { cancelAnimationFrame(animId); animId = null; }
    }

    function playUrl() {
      const url = useDirect ? au : currentApi() + '/api/audio/' + trackId + '?cid=' + getCid();
      audio.src = url;
      audio.load();
      const p = audio.play();
      if (p && p.catch) p.catch(function() {});
    }

    function play(id, name, au) {
      trackId = id;
      failed = false;
      useDirect = !!(au && au.indexOf('http') === 0);
      apiIdx = 0;
      nameEl.textContent = name;
      statusEl.textContent = '';
      statusEl.appendChild(document.createTextNode(useDirect ? '正在连接音频源…（来源站直连，无需登录）' : '正在连接音频源…（站内代理）'));
      btnPlay.textContent = '▶';
      timeEl.textContent = '0:00 / 0:00';
      if (!animId) draw();
      playUrl();
    }

    function stop() {
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
      stopAnim();
      btnPlay.textContent = '▶';
      nameEl.textContent = '';
      statusEl.textContent = '';
    }

    function markFailed() {
      failed = true;
      btnPlay.textContent = '▶';
      statusEl.textContent = '';
      if (useDirect) {
        statusEl.appendChild(document.createTextNode('播放失败：音频源连接异常，请稍后重试。'));
      } else {
        statusEl.appendChild(document.createTextNode('播放失败：请确认已登录后再试。'));
      }
    }

    let muted = false;
    let loopOn = false;
    muteBtn.onclick = function() {
      muted = !muted;
      audio.muted = muted;
      muteBtn.textContent = muted ? '🔇' : '🔊';
    };
    loopBtn.onclick = function() {
      loopOn = !loopOn;
      audio.loop = loopOn;
      loopBtn.textContent = loopOn ? '🔁' : '🔁';
      loopBtn.title = loopOn ? '单曲循环：开' : '单曲循环：关';
      if (loopOn) { loopBtn.style.color = '#fbbf24'; } else { loopBtn.style.color = ''; }
    };
    btnPlay.onclick = function() {
      if (audio.src && !audio.paused) { audio.pause(); return; }
      if (!animId) draw();
      const p = audio.play();
      if (p && p.catch) p.catch(function(e) {
        failed = true;
        statusEl.textContent = '';
        statusEl.appendChild(document.createTextNode('播放失败：' + (e && e.name ? e.name : '未知错误') + '，请点击播放键重试。'));
      });
    };
    audio.onplaying = function() {
      failed = false;
      btnPlay.textContent = '⏸';
      statusEl.textContent = '';
      if (apiIdx > 0) toast('已切换至备用线路');
    };
    audio.onpause = function() { btnPlay.textContent = '▶'; };
    audio.onended = function() { btnPlay.textContent = '▶'; };
    let retried = false;
    audio.onerror = function() {
      if (!useDirect && window.API_CANDIDATES && apiIdx + 1 < window.API_CANDIDATES.length) {
        apiIdx++;
        statusEl.textContent = '';
        statusEl.appendChild(document.createTextNode('正在切换备用线路…'));
        playUrl();
        return;
      }
      if (!retried) {
        retried = true;
        statusEl.textContent = '';
        statusEl.appendChild(document.createTextNode('线路波动，正在重试…'));
        toast('播放波动，正在重试…');
        setTimeout(function() {
          playUrl();
        }, 800);
        return;
      }
      markFailed();
    };
    audio.addEventListener('timeupdate', function() {
      const d = isFinite(audio.duration) ? audio.duration : 0;
      timeEl.textContent = fmt(audio.currentTime) + ' / ' + fmt(d);
    });
    canvas.addEventListener('click', function(e) {
      if (!isFinite(audio.duration) || audio.duration <= 0) return;
      const rect = canvas.getBoundingClientRect();
      audio.currentTime = ((e.clientX - rect.left) / rect.width) * audio.duration;
    });
    // 整块播放器区域点击也可播放/暂停（canvas 由上面 seek 逻辑接管）
    box.addEventListener('click', function(e) {
      if (e.target === canvas) return;
      if (!audio.src) return;
      if (!audio.paused) { audio.pause(); return; }
      if (!animId) draw();
      const p = audio.play();
      if (p && p.catch) p.catch(function(er) {
        failed = true;
        statusEl.textContent = '';
        statusEl.appendChild(document.createTextNode('播放失败：' + (er && er.name ? er.name : '未知错误') + '，请重试。'));
      });
    });

    function render(id, name, au) {
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
    }
    return {render: render, stop: stop};
  })();

  // ── 导航高亮 ──
  function updateNav(active) {
    document.querySelectorAll('header nav a').forEach(a => a.classList.remove('active'));
    const map = {home: 'nav-home', all: 'nav-all', dates: 'nav-dates'};
    const id = map[active];
    if (id) { const el = document.getElementById(id); if (el) el.classList.add('active'); }
  }

  // ── 路由 ──
  function route() {
    const q = getQuery();
    if (q.id) {
      if (typeof player !== 'undefined' && player) player.hide();
      renderDetail(q.id);
    } else {
      document.title = '9GDJ DJ 索引 — 单曲 / 串烧 / 中英文分类';
      if (typeof detailPlayer !== 'undefined' && detailPlayer) detailPlayer.stop();
      if (q.view === 'dates' || q.date) {
        if (q.date) renderList();
        else renderDates();
      } else if (q.format || q.lang || q.q || q.view === 'all' || q.page) {
        renderList();
      } else {
        renderHome();
      }
    }
  }

  // ── 移动端：整卡点击进详情（≤620px；排除按钮/链接/选中文本）──
  document.addEventListener('click', function(e) {
    // 进入详情前记住列表滚动位置（文件名点击 & 移动端整卡）
    const nameLink = e.target.closest('a.track-name');
    if (nameLink) sessionStorage.setItem('dj_list_scroll', String(window.scrollY || 0));
    if (window.innerWidth > 620) return;
    if (window.getSelection && window.getSelection().toString()) return;
    const tr = e.target.closest('.track-table tr');
    if (!tr) return;
    if (e.target.closest('a, button')) return;
    const link = tr.querySelector('a.track-name');
    if (link) { e.preventDefault(); location.href = link.getAttribute('href'); }
  });

  // ── PWA 安装引导（移动端；iOS 文字引导，Android 原生安装）──
  (function() {
    if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true) return;
    let deferredPrompt = null;
    const tipId = 'pwa-install-tip';
    function makeTip(text) {
      const tip = el('div', {id: tipId, class: 'pwa-tip'});
      tip.appendChild(el('div', {class: 'pwa-tip-text', text: text}));
      return tip;
    }
    window.addEventListener('beforeinstallprompt', function(e) {
      e.preventDefault();
      deferredPrompt = e;
      if (document.getElementById(tipId)) return;
      const tip = makeTip('安装 9GDJ 到主屏幕，像 App 一样秒开听歌');
      const installBtn = el('button', {type: 'button', class: 'pwa-tip-btn install', text: '安装'});
      installBtn.onclick = function() { if (deferredPrompt) deferredPrompt.prompt(); tip.remove(); };
      const closeBtn = el('button', {type: 'button', class: 'pwa-tip-btn', text: '稍后'});
      closeBtn.onclick = function() { tip.remove(); };
      tip.appendChild(installBtn);
      tip.appendChild(closeBtn);
      document.body.appendChild(tip);
      setTimeout(function() { tip.classList.add('show'); }, 800);
    });
    if (/iphone|ipad|ipod/i.test(navigator.userAgent)) {
      setTimeout(function() {
        if (document.getElementById(tipId)) return;
        const tip = makeTip('点击 Safari 分享按钮 → 「添加到主屏幕」，即可像 App 一样使用');
        const okBtn = el('button', {type: 'button', class: 'pwa-tip-btn', text: '知道了'});
        okBtn.onclick = function() { tip.remove(); };
        tip.appendChild(okBtn);
        document.body.appendChild(tip);
        setTimeout(function() { tip.classList.add('show'); }, 100);
      }, 4500);
    }
  })();

  // ── Toast ──
  function toast(msg) {
    let t = document.getElementById('toast');
    if (!t) {
      t = el('div', {class: 'toast', id: 'toast'});
      document.body.appendChild(t);
    }
    t.innerHTML = '';
    t.appendChild(document.createTextNode(msg));
    t.classList.add('show');
    clearTimeout(t._tm);
    t._tm = setTimeout(() => t.classList.remove('show'), 3200);
  }

  // ── 登录态（本地标记；官方页完成登录后确认）──
  // 部署配置：window.API_BASE 由 index.html 注入（空=同源本地；线上自动测速选择 api.9gdj.com / workers.dev）
  let API = window.API_BASE || '';
  function getCid() {
    let c = localStorage.getItem('panda_cid');
    if (!c) {
      c = 'c' + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem('panda_cid', c);
    }
    return c;
  }
  // 从文件名启发式解析艺术家
  function parseArtist(name) {
    let m = String(name || '').match(/^(.+?)\s*[-–—~]\s*(.+)$/);
    if (m) return m[1].trim();
    m = String(name || '').match(/^(.+?)[\[【（(]\s*(.+?)\s*[\]】）)]$/);
    if (m) return m[2].trim();
    return '';
  }
  // 按分类推断流派
  function inferGenre(t) {
    if (String(t.f) === '1') return 'Mashup / Non-Stop';
    if (String(t.l) === '0') return '华语舞曲';
    if (String(t.l) === '1') return 'Electronic / Remix';
    return 'Dance';
  }
  // 下载链接（带 ID3 元数据参数：曲名/艺术家/流派）
  function buildDlUrl(t) {
    const name = String(t.n || 'Track').replace(/\.(mp3|wav|flac|m4a|ogg)$/i, '');
    const artist = parseArtist(name);
    const genre = inferGenre(t);
    return (window.API_BASE || '') + '/api/download/' + t.i + '?cid=' + getCid()
      + '&n=' + encodeURIComponent(name)
      + '&a=' + encodeURIComponent(artist)
      + '&g=' + encodeURIComponent(genre);
  }
  function isAuthed() { return localStorage.getItem('panda_auth') === '1'; }
  function setAuthed(v, name) {
    if (v) {
      localStorage.setItem('panda_auth', '1');
    } else {
      localStorage.removeItem('panda_auth');
    }
    refreshAuthUI();
  }
  function refreshAuthUI() {
    const autoEl = document.getElementById('auth-auto');
    const userEl = document.getElementById('auth-user');
    const openBtn = document.getElementById('auth-open');
    const logoutBtn = document.getElementById('auth-logout');
    if (!autoEl) return;
    const showAuto = function(txt) {
      autoEl.style.display = 'inline';
      autoEl.textContent = txt || '🔓 自动授权已开启';
      if (userEl) userEl.style.display = 'none';
      if (openBtn) openBtn.style.display = 'inline-block';
      if (logoutBtn) logoutBtn.style.display = 'none';
    };
    const showUser = function(name) {
      autoEl.style.display = 'none';
      if (userEl) { userEl.style.display = 'inline'; userEl.textContent = '👤 ' + name; }
      if (openBtn) openBtn.style.display = 'none';
      if (logoutBtn) logoutBtn.style.display = 'inline-block';
    };
    fetch(API + '/api/session?cid=' + getCid()).then(function(r) { return r.json(); }).then(function(d) {
      if (d && d.ok && d.name && !d.auto) showUser(d.name);
      else showAuto('🔓 自动授权已开启');
    }).catch(function() { showAuto('🔓 自动授权已开启'); });
  }

  // ── 搜索（输入实时搜索 + 300ms 防抖 + 清除按钮）──
  function setupSearch() {
    const input = $('#search-input');
    const btn = $('#search-btn');
    const clear = $('#search-clear');
    let t = null;
    function syncClear() {
      if (clear) clear.classList.toggle('show', input.value.length > 0);
    }
    function doSearch() {
      const val = input.value.trim();
      syncClear();
      if (val) {
        setQuery({q: val, page: 1});
        route();
      }
    }
    function onInput() {
      syncClear();
      clearTimeout(t);
      t = setTimeout(function() {
        const val = input.value.trim();
        const cur = new URLSearchParams(window.location.search).get('q') || '';
        if (val && val !== cur) doSearch();
      }, 300);
    }
    if (clear) clear.onclick = function() {
      input.value = '';
      syncClear();
      input.focus();
      const cur = new URLSearchParams(window.location.search).get('q');
      if (cur) {
        setQuery({q: '', page: 1});
        route();
      }
    };
    btn.onclick = doSearch;
    input.addEventListener('input', onInput);
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') { clearTimeout(t); doSearch(); }
    });
    syncClear();
  }

  // ── 页内波纹播放器（科技风可视化；音频流对接音频接口，需登录）──
  const player = (function() {
    const bar = el('div', {class: 'player-bar', style: 'display:none;'});
    // 左：播放控制 + 时间（仿 dj024 三段式）
    const left = el('div', {class: 'player-left'});
    const btnPlay = el('button', {type: 'button', class: 'player-toggle', text: '▶', title: '播放 / 暂停'});
    const timeEl = el('div', {class: 'player-time', text: '0:00 / 0:00'});
    left.appendChild(btnPlay);
    left.appendChild(timeEl);
    // 中：曲名/状态 + 波形进度
    const mid = el('div', {class: 'player-mid'});
    const nameEl = el('div', {class: 'player-name', text: ''});
    const statusEl = el('div', {class: 'player-status'});
    const info = el('div', {class: 'player-info'});
    info.appendChild(nameEl);
    info.appendChild(statusEl);
    mid.appendChild(info);
    const canvas = el('canvas', {class: 'player-wave'});
    canvas.width = 460;
    canvas.height = 48;
    const ctx = canvas.getContext('2d');
    mid.appendChild(canvas);
    // 右：音量 + 单曲循环 + 关闭
    const right = el('div', {class: 'player-right'});
    const muteBtn = el('button', {type: 'button', class: 'player-btn', text: '🔊', title: '静音'});
    const loopBtn = el('button', {type: 'button', class: 'player-btn', text: '🔁', title: '单曲循环：关'});
    const closeBtn = el('button', {type: 'button', class: 'player-close', text: '×', title: '关闭播放器'});
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
    let apiIdx = 0;
    function currentApi() {
      return (window.API_CANDIDATES && window.API_CANDIDATES[apiIdx]) || API;
    }

    function fmt(s) {
      if (!isFinite(s) || s < 0) s = 0;
      return Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
    }

    function draw() {
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);
      const t = performance.now() / 1000;
      const bars = 52;
      const bw = W / bars;
      const playing = !audio.paused && !audio.ended && !failed && audio.readyState > 0;
      for (let i = 0; i < bars; i++) {
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
      }
      const prog = audio.duration > 0 ? Math.min(1, audio.currentTime / audio.duration) : 0;
      if (prog < 1) {
        ctx.fillStyle = 'rgba(8,12,24,0.55)';
        ctx.fillRect(prog * W, 0, W * (1 - prog), H);
      }
      if (prog > 0) {
        ctx.fillStyle = 'rgba(255,255,255,0.85)';
        ctx.fillRect(prog * W - 1.5, 0, 3, H);
      }
      animId = requestAnimationFrame(draw);
    }

    function stopAnim() {
      if (animId) { cancelAnimationFrame(animId); animId = null; }
    }

    function playUrl() {
      const url = useDirect ? au : currentApi() + '/api/audio/' + trackId + '?cid=' + getCid();
      audio.src = url;
      audio.load();
      const p = audio.play();
      if (p && p.catch) p.catch(function() {});
    }

    function show(id, name, au) {
      trackId = id;
      failed = false;
      useDirect = !!(au && au.indexOf('http') === 0);
      apiIdx = 0;
      retried = false;
      nameEl.textContent = name;
      statusEl.textContent = '';
      statusEl.appendChild(document.createTextNode(useDirect ? '正在连接音频源…（来源站直连，无需登录）' : '正在连接音频源…（站内代理）'));
      btnPlay.textContent = '▶';
      timeEl.textContent = '0:00 / 0:00';
      bar.style.display = 'flex';
      if (!animId) draw();
      playUrl();
    }

    function hide() {
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
      stopAnim();
      bar.style.display = 'none';
    }

    function markFailed() {
      failed = true;
      btnPlay.textContent = '▶';
      statusEl.textContent = '';
      if (useDirect) {
        statusEl.appendChild(document.createTextNode('播放失败：音频源连接异常，请稍后重试。'));
      } else {
        statusEl.appendChild(document.createTextNode('播放失败：请确认已登录后再试。'));
      }
    }

    let muted = false;
    let loopOn = false;
    muteBtn.onclick = function() {
      muted = !muted;
      audio.muted = muted;
      muteBtn.textContent = muted ? '🔇' : '🔊';
      muteBtn.title = muted ? '取消静音' : '静音';
    };
    loopBtn.onclick = function() {
      loopOn = !loopOn;
      audio.loop = loopOn;
      loopBtn.classList.toggle('on', loopOn);
      loopBtn.title = loopOn ? '单曲循环：开' : '单曲循环：关';
    };
    closeBtn.onclick = hide;
    btnPlay.onclick = function() {
      if (audio.paused) { const p = audio.play(); if (p && p.catch) p.catch(function() {}); }
      else audio.pause();
    };
    audio.onplaying = function() {
      failed = false;
      btnPlay.textContent = '⏸';
      statusEl.textContent = '';
      if (apiIdx > 0) toast('已切换至备用线路');
    };
    audio.onpause = function() { btnPlay.textContent = '▶'; };
    audio.onended = function() {
      btnPlay.textContent = '▶';
    };
    let retried = false;
    audio.onerror = function() {
      if (!useDirect && window.API_CANDIDATES && apiIdx + 1 < window.API_CANDIDATES.length) {
        apiIdx++;
        statusEl.textContent = '';
        statusEl.appendChild(document.createTextNode('正在切换备用线路…'));
        playUrl();
        return;
      }
      if (!retried) {
        retried = true;
        statusEl.textContent = '';
        statusEl.appendChild(document.createTextNode('线路波动，正在重试…'));
        toast('播放波动，正在重试…');
        setTimeout(function() {
          playUrl();
        }, 800);
        return;
      }
      markFailed();
    };
    audio.addEventListener('timeupdate', function() {
      const d = isFinite(audio.duration) ? audio.duration : 0;
      timeEl.textContent = fmt(audio.currentTime) + ' / ' + fmt(d);
    });
    canvas.addEventListener('click', function(e) {
      if (!isFinite(audio.duration) || audio.duration <= 0) return;
      const rect = canvas.getBoundingClientRect();
      audio.currentTime = ((e.clientX - rect.left) / rect.width) * audio.duration;
    });
    return {show: show, hide: hide};
  })();

  // ── 注册/登录模态框（白牌） ──
  const auth = (function() {
    const overlay = document.getElementById('auth-overlay');
    if (!overlay) return null;
    const tabs = overlay.querySelectorAll('.auth-tab');
    const formReg = document.getElementById('auth-form-register');
    const formLog = document.getElementById('auth-form-login');
    const titleEl = document.getElementById('auth-title');
    function switchTab(mode) {
      tabs.forEach(t => t.classList.toggle('on', t.dataset.tab === mode));
      if (formReg) formReg.style.display = mode === 'register' ? '' : 'none';
      if (formLog) formLog.style.display = mode === 'login' ? '' : 'none';
      if (titleEl) titleEl.textContent = mode === 'register' ? '注册新账号' : '登录';
    }
    function open(mode) {
      switchTab(mode || 'register');
      overlay.classList.add('show');
    }
    function close() { overlay.classList.remove('show'); }
    function setNote(id, msg) { const n = document.getElementById(id); if (n) n.textContent = msg; }
    function busy(btn, on) {
      if (!btn) return;
      btn.disabled = on;
      btn.textContent = on ? '提交中…' : (btn.id === 'auth-submit-register' ? '注册' : '登录');
    }
    async function submitRegister() {
      const name = (document.getElementById('auth-name') || {}).value || '';
      const email = (document.getElementById('auth-email') || {}).value || '';
      const pass = (document.getElementById('auth-pass') || {}).value || '';
      const pass2 = (document.getElementById('auth-pass2') || {}).value || '';
      if (!name || !email || !pass || !pass2) { setNote('auth-note-register', '请填写完整信息。'); return; }
      if (pass !== pass2) { setNote('auth-note-register', '两次输入的密码不一致。'); return; }
      const btn = document.getElementById('auth-submit-register');
      busy(btn, true);
      try {
        const r = await fetch(API + '/api/register?cid=' + getCid(), {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Client-Id': getCid()}, body: JSON.stringify({name: name, email: email, password: pass})});
        const d = await r.json();
        if (d.ok) { setAuthed(true, d.name); close(); toast('注册成功，已自动登录。'); }
        else setNote('auth-note-register', d.msg || '注册失败，请稍后重试。');
      } catch (err) { setNote('auth-note-register', '网络异常，请稍后重试。'); }
      busy(btn, false);
    }
    async function submitLogin() {
      const email = (document.getElementById('auth-login-email') || {}).value || '';
      const pass = (document.getElementById('auth-login-pass') || {}).value || '';
      if (!email || !pass) { setNote('auth-note-login', '请填写邮箱和密码。'); return; }
      const btn = document.getElementById('auth-submit-login');
      busy(btn, true);
      try {
        const r = await fetch(API + '/api/login?cid=' + getCid(), {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Client-Id': getCid()}, body: JSON.stringify({email: email, password: pass})});
        const d = await r.json();
        if (d.ok) { setAuthed(true, d.name); close(); toast('登录成功。'); }
        else setNote('auth-note-login', d.msg || '登录失败，请稍后重试。');
      } catch (err) { setNote('auth-note-login', '网络异常，请稍后重试。'); }
      busy(btn, false);
    }
    tabs.forEach(t => t.onclick = () => switchTab(t.dataset.tab));
    const closeBtn = document.getElementById('auth-close');
    if (closeBtn) closeBtn.onclick = close;
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
    const sr = document.getElementById('auth-submit-register');
    const sl = document.getElementById('auth-submit-login');
    if (sr) sr.onclick = submitRegister;
    if (sl) sl.onclick = submitLogin;
    return {open: open, close: close};
  })();

  // 导航栏登录/登出按钮
  const authOpenBtn = document.getElementById('auth-open');
  if (authOpenBtn) authOpenBtn.onclick = function() { if (auth) auth.open('login'); };
  const authLogoutBtn = document.getElementById('auth-logout');
  if (authLogoutBtn) authLogoutBtn.onclick = function() {
    try { fetch(API + '/api/logout?cid=' + getCid()); } catch (e) {}
    setAuthed(false);
    toast('已退出登录。');
  };
  // 页头注册/登录入口
  document.addEventListener('click', function(e) {
    const b = e.target.closest ? e.target.closest('.auth-entry') : null;
    if (b && auth) {
      e.preventDefault();
      if (b.id === 'auth-login' && isAuthed()) {
        try { fetch(API + '/api/logout?cid=' + getCid()); } catch (e) {}
        setAuthed(false);
        toast('已退出登录。');
        return;
      }
      auth.open(b.id === 'auth-login' ? 'login' : 'register');
    }
  });

  // 文件名点击：未登录不可进入详情（站内底层页）
  document.addEventListener('click', function(e) {
    const a = e.target.closest ? e.target.closest('a.track-name') : null;
    if (a) {
      if (!isAuthed()) {
        e.preventDefault();
        if (auth) {
          auth.open('login');
          const note = document.getElementById('auth-note-login');
          if (note) note.textContent = '登录后即可查看曲目详情与完整播放。';
        }
        toast('登录后可查看曲目详情。');
      } else {
        e.preventDefault();
        setQuery({id: a.dataset.id});
        route();
        window.scrollTo({top: 0, behavior: 'smooth'});
      }
    }
  });

  // 试听按钮事件委托（覆盖 JS 渲染行与首页预渲染行；单曲播放）
  document.addEventListener('click', function(e) {
    const btn = e.target.closest ? e.target.closest('.act-listen') : null;
    if (btn) {
      e.preventDefault();
      player.show(btn.dataset.id, btn.dataset.name, btn.dataset.au);
    }
  });

  // 下载按钮：未登录拦截 + 下载反馈
  document.addEventListener('click', function(e) {
    const a = e.target.closest ? e.target.closest('a.act-download, a.track-download') : null;
    if (a) {
      if (!isAuthed()) {
        e.preventDefault();
        if (auth) auth.open('login');
        toast('登录后可下载曲目。');
      } else {
        toast('正在准备下载…');
      }
    }
  });

  // ── 初始化 ──
  window.addEventListener('DOMContentLoaded', async () => {
    // 双 API 自动选择：api.9gdj.com（国内可达）优先，workers.dev 兜底
    if (window.resolveApi) { await window.resolveApi(); API = window.API_BASE; }
    setupSearch();
    refreshAuthUI();
    // 校验后台会话（服务重启后自动登出）
    fetch(API + '/api/session?cid=' + getCid()).then(r => r.json()).then(d => { setAuthed(!!d.ok, d.name); }).catch(() => {});
    const ok = await loadData();
    if (ok) {
      route();
      window.addEventListener('popstate', route);
    }
  });
})();
