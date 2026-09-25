// Cloudflare Worker: pandadj 白牌代理（注册/登录/会话/试听/下载）
// KV: SESSIONS  ->  cid -> {cookies: string[], email, name}
// 前端 API: /api/register /api/login /api/logout /api/session /api/audio/:id /api/download/:id
// cid 通过 X-Client-Id 头或 ?cid= 传入，用于多会话隔离

const PANDADJ = 'https://pandadj.com';
const UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-Client-Id',
  'Access-Control-Max-Age': '600',
};

function json(code, obj) {
  return new Response(JSON.stringify(obj), {
    status: code,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...CORS },
  });
}

function getCid(request, url) {
  const q = url.searchParams.get('cid');
  if (q) return q;
  return request.headers.get('X-Client-Id') || 'local';
}

function extractToken(html, cookies) {
  const m = html.match(/name="_token"\s+value="([^"]+)"/);
  if (m) return m[1];
  const xsrf = cookies.find((c) => c.startsWith('XSRF-TOKEN='));
  if (xsrf) {
    try { return decodeURIComponent(xsrf.slice(11)).replace(/^"|"$/g, ''); } catch (e) { return xsrf.slice(11); }
  }
  return '';
}

function collectSetCookies(headers) {
  const out = [];
  if (typeof headers.getSetCookie === 'function') {
    for (const c of headers.getSetCookie()) out.push(c.split(';')[0]);
  } else {
    headers.forEach((v, k) => { if (k.toLowerCase() === 'set-cookie') out.push(v.split(';')[0]); });
  }
  return out.filter(Boolean);
}

function mergeCookies(existing, fresh) {
  const map = new Map();
  for (const c of existing || []) {
    const k = c.split('=')[0];
    if (k) map.set(k, c);
  }
  for (const c of fresh || []) {
    const k = c.split('=')[0];
    if (k) map.set(k, c);
  }
  return [...map.values()];
}

async function getCtx(env, cid) {
  if (!cid) return null;
  const v = await env.SESSIONS.get(cid, { type: 'json' });
  return v || null;
}
async function setCtx(env, cid, ctx) {
  if (!ctx) { await env.SESSIONS.delete(cid); return; }
  await env.SESSIONS.put(cid, JSON.stringify(ctx));
}
async function proxyAuthPage(path) {
  const r = await fetch(PANDADJ + path, { headers: { 'User-Agent': UA } });
  const html = await r.text();
  const cookies = collectSetCookies(r.headers);
  return { html, cookies, token: extractToken(html, cookies) };
}

async function proxySubmit(path, token, cookies, fields) {
  const body = new URLSearchParams({ _token: token, ...fields });
  const r = await fetch(PANDADJ + path, {
    method: 'POST',
    redirect: 'follow',
    headers: {
      'User-Agent': UA,
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'text/html,application/xhtml+xml',
      'Referer': PANDADJ + path,
      'Cookie': cookies.join('; '),
    },
    body,
  });
  const fresh = collectSetCookies(r.headers);
  return { status: r.status, url: r.url, cookies: mergeCookies(cookies, fresh) };
}

async function proxyStream(path, ctx, request) {
  const headers = { 'User-Agent': UA };
  if (ctx && ctx.cookies && ctx.cookies.length) headers['Cookie'] = ctx.cookies.join('; ');
  const range = request.headers.get('Range');
  if (range) headers['Range'] = range;
  const r = await fetch(PANDADJ + path, { headers });
  const ct = (r.headers.get('Content-Type') || '').toLowerCase();
  if (r.status === 200 || r.status === 206) {
    if (!ct.includes('audio') && !ct.includes('octet-stream')) {
      // 未登录时 pandadj 302 到登录页，follow 后拿到 HTML
      const body = await r.text();
      if (/login|register/i.test(body.slice(0, 2000))) {
        return json(401, { ok: false, msg: '未登录' });
      }
      return new Response(body, { status: 502, headers: { 'Content-Type': ct, ...CORS } });
    }
    const respHeaders = {
      'Content-Type': r.headers.get('Content-Type') || 'audio/mpeg',
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'no-store',
      ...CORS,
    };
    if (r.headers.get('Content-Length')) respHeaders['Content-Length'] = r.headers.get('Content-Length');
    if (r.headers.get('Content-Range')) respHeaders['Content-Range'] = r.headers.get('Content-Range');
    if (path.startsWith('/transload/download/')) {
      const id = path.split('/').pop();
      respHeaders['Content-Disposition'] = `attachment; filename="${id}.mp3"`;
    }
    return new Response(r.body, { status: r.status, headers: respHeaders });
  }
  return json(502, { ok: false, msg: '音频源响应异常 ' + r.status });
}

async function handle(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;
  const cid = getCid(request, url);

  // CORS 预检
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: CORS });
  }

  // ── 注册 ──
  if (request.method === 'POST' && path === '/api/register') {
    let body = {};
    try { body = await request.json(); } catch (e) {}
    const name = (body.name || '').trim();
    const email = (body.email || '').trim();
    const password = body.password || '';
    if (!name || !email || !password) return json(400, { ok: false, msg: '请填写完整信息' });
    if (!email.includes('@') || password.length < 6) return json(400, { ok: false, msg: '邮箱格式或密码长度不正确（密码至少 6 位）' });
    try {
      const page = await proxyAuthPage('/register');
      if (!page.token) return json(502, { ok: false, msg: '无法连接注册服务，请稍后重试' });
      const res = await proxySubmit('/register', page.token, page.cookies, {
        name, email, password, password_confirmation: password,
      });
      const ok = res.status === 200 && !res.url.includes('/register');
      if (ok) {
        const ctx = { cookies: res.cookies, email, name, time: Date.now() };
        await env.SESSIONS.put(cid, JSON.stringify(ctx));
        return json(200, { ok: true, msg: '注册成功，已自动登录', name });
      }
      return json(400, { ok: false, msg: '注册失败：邮箱可能已被使用，请尝试登录或更换邮箱' });
    } catch (e) {
      return json(502, { ok: false, msg: '注册服务异常' });
    }
  }

  // ── 登录 ──
  if (request.method === 'POST' && path === '/api/login') {
    let body = {};
    try { body = await request.json(); } catch (e) {}
    const email = (body.email || '').trim();
    const password = body.password || '';
    if (!email || !password) return json(400, { ok: false, msg: '请填写邮箱和密码' });
    try {
      const page = await proxyAuthPage('/login');
      if (!page.token) return json(502, { ok: false, msg: '无法连接登录服务，请稍后重试' });
      const res = await proxySubmit('/login', page.token, page.cookies, { email, password });
      const ok = res.status === 200 && !res.url.includes('/login');
      if (ok) {
        const old = await env.SESSIONS.get(cid, { type: 'json' });
        const ctx = { cookies: res.cookies, email, name: (old && old.name) || '', time: Date.now() };
        await env.SESSIONS.put(cid, JSON.stringify(ctx));
        return json(200, { ok: true, msg: '登录成功', name: ctx.name });
      }
      return json(401, { ok: false, msg: '登录失败：邮箱或密码不正确' });
    } catch (e) {
      return json(502, { ok: false, msg: '登录服务异常' });
    }
  }

  // ── 登出 ──
  if (path === '/api/logout') {
    await env.SESSIONS.delete(cid);
    return json(200, { ok: true });
  }

  // ── 会话状态 ──
  if (path === '/api/session') {
    const ctx = await env.SESSIONS.get(cid, { type: 'json' });
    if (ctx && ctx.cookies && ctx.cookies.length) {
      return json(200, { ok: true, email: ctx.email || '', name: ctx.name || '' });
    }
    return json(200, { ok: false, email: '', name: '' });
  }

  // ── 试听/下载代理 ──
  const m = path.match(/^\/api\/(audio|download)\/(\d+)$/);
  if (m && request.method === 'GET') {
    const kind = m[1];
    const tid = m[2];
    const ctx = await env.SESSIONS.get(cid, { type: 'json' });
    if (!ctx || !ctx.cookies || !ctx.cookies.length) return json(401, { ok: false, msg: '未登录' });
    return proxyStream('/transload/download/' + tid, ctx, request, kind);
  }

  return json(404, { ok: false, msg: 'not found' });
}

export default {
  async fetch(request, env, ctx) {
    try {
      return await handle(request, env);
    } catch (e) {
      return json(500, { ok: false, msg: 'internal error' });
    }
  },
};
