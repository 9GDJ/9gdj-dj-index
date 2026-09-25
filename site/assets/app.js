/* ===== 9GDJ DJ 索引 — 客户端逻辑 ===== */
(function() {
  'use strict';

  const PAGE_SIZE = 50;
  let ALL_TRACKS = null;
  let STATS = null;
  let DATES = null;
  let currentPage = 1;
  let filtered = null;

  const FORMAT_NAMES = ['单曲', '串烧'];
  const LANG_NAMES = ['中文', '英文', '其他'];

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
    const qs = new URLSearchParams(params).toString();
    const url = qs ? '?' + qs : window.location.pathname;
    window.history.pushState({}, '', url);
  }

  // ── 数据加载 ──
  async function loadData() {
    showLoading('正在加载曲目数据...');
    try {
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
    } catch (e) {
      showLoading('数据加载失败: ' + e.message);
      return false;
    }
  }

  function showLoading(msg) {
    const m = $('#main');
    m.innerHTML = '<div class="loading"><div class="spinner"></div>' + (msg || '加载中...') + '</div>';
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
      tagTd.appendChild(el('span', {class: 'tag tag-' + (t.l === 0 ? 'zh' : t.l === 1 ? 'en' : 'other'), text: LANG_NAMES[t.l]}));
      tr.appendChild(tagTd);
      const actTd = el('td', {class: 'col-actions'});
      const dlUrl = API + '/api/download/' + t.i + '?cid=' + getCid();
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

    // 统计卡片
    const statsGrid = el('div', {class: 'stats-grid'});
    const cards = [
      [STATS.total, '曲目总数'],
      [STATS.format.single || 0, '单曲'],
      [STATS.format.mashup || 0, '串烧'],
      [STATS.language.zh || 0, '中文'],
      [STATS.language.en || 0, '英文'],
      [STATS.today_count || 0, '今日新增'],
    ];
    cards.forEach(([num, label]) => {
      const card = el('div', {class: 'stat-card'});
      card.appendChild(el('div', {class: 'num', text: num.toLocaleString()}));
      card.appendChild(el('div', {class: 'label', text: label}));
      statsGrid.appendChild(card);
    });
    m.appendChild(statsGrid);

    // 分类入口
    m.appendChild(el('div', {class: 'section-title', text: '分类浏览'}));
    const catGrid = el('div', {class: 'cat-grid'});
    const cats = [
      ['全部单曲', 'format=single', STATS.format.single || 0],
      ['全部串烧', 'format=mashup', STATS.format.mashup || 0],
      ['中文单曲', 'format=single&lang=zh', STATS.combo.zh_single || 0],
      ['英文单曲', 'format=single&lang=en', STATS.combo.en_single || 0],
      ['中文串烧', 'format=mashup&lang=zh', STATS.combo.zh_mashup || 0],
      ['英文串烧', 'format=mashup&lang=en', STATS.combo.en_mashup || 0],
    ];
    cats.forEach(([name, qs, count]) => {
      const card = el('a', {href: '?' + qs, class: 'cat-card'});
      card.appendChild(el('span', {class: 'cat-name', text: name}));
      card.appendChild(el('span', {class: 'cat-count', text: count.toLocaleString()}));
      catGrid.appendChild(card);
    });
    m.appendChild(catGrid);

    // 最新入库
    m.appendChild(el('div', {class: 'section-title', text: '最新入库'}));
    const latest = ALL_TRACKS.slice(0, 30);
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
  function renderList() {
    const q = getQuery();
    const m = $('#main');
    m.innerHTML = '';

    // 面包屑
    const bc = el('div', {class: 'breadcrumb'});
    bc.appendChild(el('a', {href: '?', text: '首页'}));
    bc.appendChild(el('span', {class: 'sep', text: '/'}));
    let title = '全部曲目';
    if (q.format) title = (q.format === 'mashup' ? '串烧' : '单曲');
    if (q.lang) title = (q.lang === 'zh' ? '中文' : q.lang === 'en' ? '英文' : '其他') + title;
    if (q.q) title = '搜索: "' + q.q + '"';
    if (q.date) title = q.date + ' 入库';
    bc.appendChild(el('span', {text: title}));
    m.appendChild(bc);

    // 过滤
    let result = ALL_TRACKS;
    if (q.format) result = result.filter(t => (q.format === 'mashup' ? t.f === 1 : t.f === 0));

    if (q.lang) result = result.filter(t => (q.lang === 'zh' ? t.l === 0 : q.lang === 'en' ? t.l === 1 : t.l === 2));
    if (q.date) result = result.filter(t => t.d === q.date);
    if (q.q) {
      const kw = q.q.toLowerCase();
      result = result.filter(t => t.n.toLowerCase().includes(kw));
    }
    filtered = result;

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
    [['', '全部语言'], ['zh', '中文'], ['en', '英文'], ['other', '其他']].forEach(([v, label]) => {
      const o = el('option', {value: v, text: label});
      if (q.lang === v) o.selected = true;
      langSel.appendChild(o);
    });
    langSel.onchange = () => { const nq = getQuery(); nq.lang = langSel.value; if(!nq.lang) delete nq.lang; nq.page=1; setQuery(nq); renderList(); };
    bar.appendChild(langSel);

    bar.appendChild(el('span', {class: 'result-count', text: '共 ' + result.length.toLocaleString() + ' 条'}));
    m.appendChild(bar);

    // 分页
    const page = parseInt(q.page) || 1;
    const start = (page - 1) * PAGE_SIZE;
    const pageTracks = result.slice(start, start + PAGE_SIZE);
    renderTrackTable(pageTracks, m);
    renderPagination(result.length, page, m, (p) => {
      const nq = getQuery(); nq.page = p; setQuery(nq); renderList();
      window.scrollTo({top: 0, behavior: 'smooth'});
    });

    updateNav(q.format || q.q || q.date ? 'list' : 'all');
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
  function renderDetail(id) {
    const m = $('#main');
    m.innerHTML = '';
    const t = ALL_TRACKS.find(x => String(x.i) === String(id));
    if (!t) {
      m.appendChild(el('div', {class: 'loading', text: '未找到该曲目 (ID=' + id + ')'}));
      return;
    }
    const bc = el('div', {class: 'breadcrumb'});
    bc.appendChild(el('a', {href: '?', text: '首页'}));
    bc.appendChild(el('span', {class: 'sep', text: '/'}));
    bc.appendChild(el('span', {text: '曲目详情'}));
    m.appendChild(bc);

    const wrap = el('div', {class: 'detail-wrap'});
    wrap.appendChild(el('div', {class: 'detail-title', text: t.n}));

    const meta = el('div', {class: 'detail-meta'});
    const fmtName = FORMAT_NAMES[t.f === 1 ? 1 : 0];
    const langName = LANG_NAMES[t.l === 0 ? 0 : t.l === 1 ? 1 : 2];
    [['编号', String(t.i)], ['大小', t.s != null ? t.s + ' MiB' : '-'], ['入库时间', t.t || '-'], ['格式', fmtName], ['语言', langName]].forEach(([k, v]) => {
      const cell = el('div', {class: 'm'});
      cell.appendChild(el('div', {class: 'k', text: k}));
      cell.appendChild(el('div', {class: 'v', text: v}));
      meta.appendChild(cell);
    });
    wrap.appendChild(meta);

    const links = el('div', {class: 'detail-links'});
    if (t.u) links.appendChild(el('a', {href: t.u, target: '_blank', rel: 'noopener', text: '来源站页面 ↗'}));
    links.appendChild(el('a', {href: API + '/api/download/' + t.i + '?cid=' + getCid(), class: 'track-download', text: '下载', download: t.n}));
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

    function play(id, name, au) {
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
      if (p && p.catch) p.catch(function() {});
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
    audio.onplaying = function() { failed = false; btnPlay.textContent = '⏸'; statusEl.textContent = ''; };
    audio.onpause = function() { btnPlay.textContent = '▶'; };
    audio.onended = function() { btnPlay.textContent = '▶'; };
    audio.onerror = function() { markFailed(); };
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
    document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
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
  // 部署配置：window.API_BASE 由 index.html 注入（空=同源本地；GitHub Pages 部署时填后端地址）
  const API = window.API_BASE || '';
  function getCid() {
    let c = localStorage.getItem('panda_cid');
    if (!c) {
      c = 'c' + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem('panda_cid', c);
    }
    return c;
  }
  function isAuthed() { return localStorage.getItem('panda_auth') === '1'; }
  function setAuthed(v, name) {
    if (v) {
      localStorage.setItem('panda_auth', '1');
      if (name) localStorage.setItem('panda_name', name);
    } else {
      localStorage.removeItem('panda_auth');
      localStorage.removeItem('panda_name');
    }
    refreshAuthUI();
  }
  function refreshAuthUI() {
    // 昵称显示模块已移除（仅保留自动授权标识）
  }

  // ── 搜索 ──
  function setupSearch() {
    const input = $('#search-input');
    const btn = $('#search-btn');
    function doSearch() {
      const val = input.value.trim();
      if (val) {
        setQuery({q: val, page: 1});
        route();
      }
    }
    btn.onclick = doSearch;
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
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

    function show(id, name, au) {
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
      if (p && p.catch) p.catch(function() {});
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
    audio.onplaying = function() { failed = false; btnPlay.textContent = '⏸'; statusEl.textContent = ''; };
    audio.onpause = function() { btnPlay.textContent = '▶'; };
    audio.onended = function() { btnPlay.textContent = '▶'; };
    audio.onerror = function() { markFailed(); };
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

  // ── 注册/登录模块已移除（免登录自动授权）──
  const auth = null;

  // 文件名点击：进入详情（免登录自动授权后直接放行）
  document.addEventListener('click', function(e) {
    const a = e.target.closest ? e.target.closest('a.track-name') : null;
    if (a) {
      if (!isAuthed()) {
        e.preventDefault();
        toast('加载中，请稍候…');
      } else {
        e.preventDefault();
        setQuery({id: a.dataset.id});
        route();
        window.scrollTo({top: 0, behavior: 'smooth'});
      }
    }
  });

  // 试听按钮事件委托（覆盖 JS 渲染行与首页预渲染行）
  document.addEventListener('click', function(e) {
    const btn = e.target.closest ? e.target.closest('.act-listen') : null;
    if (btn) {
      e.preventDefault();
      player.show(btn.dataset.id, btn.dataset.name, btn.dataset.au);
    }
  });

  // 下载按钮：免登录自动授权后直接下载（后端自动登录）
  document.addEventListener('click', function(e) {
    const a = e.target.closest ? e.target.closest('a.act-download') : null;
    if (a && !isAuthed()) {
      e.preventDefault();
      toast('下载通道准备中，请稍候…');
    }
  });

  // ── 初始化 ──
  window.addEventListener('DOMContentLoaded', async () => {
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
