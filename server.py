# -*- coding: utf-8 -*-
"""panda-index-site 本地一体化服务：静态站点 + 后台代理（注册/登录/试听/下载全站内完成，不跳转官方界面）"""
import io
import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

import hashlib
import requests

SITE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site')
_USERS_FILE = os.environ.get('USERS_FILE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json'))
PORT = int(os.environ.get('PORT', '8765'))
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')
PANDADJ = 'https://pandadj.com'
TIMEOUT = 30

UA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

_lock = threading.Lock()
_sessions = {}           # cid -> {s, email, name, time}（多用户会话隔离）
_users = {}              # 注册昵称内存表：email -> name
DEFAULT_CID = 'local'
_auto_ctx = None         # 兼容旧引用
_auto_sessions = {}     # email -> {s, email, name, time} 账号池会话（按账号复用）
AUTO_EMAIL = 'persistnick1@yopmail.com'
AUTO_PASSWORD = 'TestPw!123456'
# 免登录账号池：按访客 IP 哈希分配，多账号分担避免单账号高频触发源站风控
ACCOUNTS = [
    {'email': 'persistnick1@yopmail.com', 'password': 'TestPw!123456'},
    {'email': 'runtimenick1@yopmail.com', 'password': 'TestPw!123456'},
]


def new_session():
    s = requests.Session()
    s.headers.update(UA)
    return s


def fetch_token(s, path):
    r = s.get(PANDADJ + path, timeout=TIMEOUT)
    m = re.search(r'name="_token" value="([^"]+)"', r.text)
    tok = m.group(1) if m else None
    if not tok:
        xsrf = s.cookies.get('XSRF-TOKEN')
        if xsrf:
            tok = unquote(xsrf).strip('"')
    return tok


def do_register(name, email, password):
    s = new_session()
    tok = fetch_token(s, '/register')
    if not tok:
        return False, '无法连接注册服务，请稍后重试'
    data = {
        '_token': tok,
        'name': name,
        'email': email,
        'password': password,
        'password_confirmation': password,
    }
    r = s.post(PANDADJ + '/register', data=data, allow_redirects=True, timeout=TIMEOUT)
    # Laravel 注册成功自动登录并跳转首页；失败回显注册页
    if r.status_code == 200 and 'register' not in r.url:
        return s, '注册成功，已自动登录'
    # 常见失败：邮箱已注册 / 字段校验
    if 'register' in r.url or r.status_code in (302, 303):
        return False, '注册失败：邮箱可能已被使用，请尝试登录或更换邮箱'
    return False, '注册失败，请稍后重试'


def do_login(email, password):
    s = new_session()
    tok = fetch_token(s, '/login')
    if not tok:
        return False, '无法连接登录服务，请稍后重试'
    data = {'_token': tok, 'email': email, 'password': password}
    r = s.post(PANDADJ + '/login', data=data, allow_redirects=True, timeout=TIMEOUT)
    if r.status_code == 200 and 'login' not in r.url:
        return s, '登录成功'
    return False, '登录失败：邮箱或密码不正确'


def load_users():
    global _users
    try:
        with io.open(_USERS_FILE, 'r', encoding='utf-8') as f:
            _users = json.load(f)
    except Exception:
        _users = {}


def save_users():
    try:
        with io.open(_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(_users, f, ensure_ascii=False)
    except Exception:
        pass


def set_ctx(cid, s, email, name=''):
    if not cid:
        cid = DEFAULT_CID
    if s is None:
        _sessions.pop(cid, None)
        return
    _sessions[cid] = {'s': s, 'email': email, 'name': name, 'time': time.time()}


def get_ctx(cid):
    if not cid:
        cid = DEFAULT_CID
    return _sessions.get(cid)


def get_client_ip(handler):
    """取访客 IP：优先 X-Forwarded-For（部署在反代/云后），否则直连 IP"""
    xff = handler.headers.get('X-Forwarded-For')
    if xff:
        return xff.split(',')[0].strip()
    return handler.client_address[0]


def pick_account(ip):
    """按 IP 稳定哈希分配账号（同一 IP 始终同一账号）"""
    if not ACCOUNTS:
        return {'email': AUTO_EMAIL, 'password': AUTO_PASSWORD}
    idx = int(hashlib.md5(ip.encode('utf-8')).hexdigest(), 16) % len(ACCOUNTS)
    return ACCOUNTS[idx]


def ensure_auto_for(email):
    """按账号邮箱取/建免登录会话"""
    ctx = _auto_sessions.get(email)
    if ctx and ctx.get('s'):
        return ctx
    acc = next((a for a in ACCOUNTS if a['email'] == email), {'email': AUTO_EMAIL, 'password': AUTO_PASSWORD})
    s, msg = do_login(acc['email'], acc['password'])
    if isinstance(s, requests.Session):
        ctx = {'s': s, 'email': acc['email'], 'name': acc['email'].split('@')[0], 'time': time.time()}
        _auto_sessions[acc['email']] = ctx
        return ctx
    return None


def ensure_auto(ip=''):
    """免登录自动授权：按访客 IP 分配账号，首次登录后该账号会话全局复用"""
    return ensure_auto_for(pick_account(ip or DEFAULT_CID)['email'])


def proxy_stream(s, path, client_headers):
    headers = {'User-Agent': UA['User-Agent']}
    rng = client_headers.get('Range')
    if rng:
        headers['Range'] = rng
    r = s.get(PANDADJ + path, headers=headers, stream=True, timeout=TIMEOUT)
    return r


MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.webmanifest': 'application/manifest+json',
}


class Handler(BaseHTTPRequestHandler):
    server_version = 'PandaIndex/1.0'
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        pass

    def _cors(self):
        if ALLOWED_ORIGIN and ALLOWED_ORIGIN != '*':
            self.send_header('Access-Control-Allow-Origin', ALLOWED_ORIGIN)
            self.send_header('Vary', 'Origin')
        else:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Client-Id')
        self.send_header('Access-Control-Max-Age', '600')

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        ln = int(self.headers.get('Content-Length') or 0)
        if ln <= 0:
            return {}
        raw = self.rfile.read(ln)
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception:
            return {}

    def _api(self):
        path = urlparse(self.path).path
        qs = urlparse(self.path).query
        cid = None
        for kv in qs.split('&'):
            if kv.startswith('cid='):
                cid = kv[4:]
        cid = cid or self.headers.get('X-Client-Id') or DEFAULT_CID
        # ── 注册 ──
        if self.command == 'POST' and path == '/api/register':
            b = self._read_body()
            name = (b.get('name') or '').strip()
            email = (b.get('email') or '').strip()
            password = b.get('password') or ''
            if not all([name, email, password]):
                return self._json(400, {'ok': False, 'msg': '请填写完整信息'})
            if '@' not in email or len(password) < 6:
                return self._json(400, {'ok': False, 'msg': '邮箱格式或密码长度不正确（密码至少 6 位）'})
            s, msg = do_register(name, email, password)
            if isinstance(s, requests.Session):
                with _lock:
                    _users[email] = name
                    save_users()
                    set_ctx(cid, s, email, name)
                return self._json(200, {'ok': True, 'msg': msg, 'name': name})
            return self._json(400, {'ok': False, 'msg': msg})
        # ── 登录 ──
        if self.command == 'POST' and path == '/api/login':
            b = self._read_body()
            email = (b.get('email') or '').strip()
            password = b.get('password') or ''
            if not email or not password:
                return self._json(400, {'ok': False, 'msg': '请填写邮箱和密码'})
            s, msg = do_login(email, password)
            if isinstance(s, requests.Session):
                with _lock:
                    nm = _users.get(email, '') or email.split('@')[0]
                    set_ctx(cid, s, email, nm)
                return self._json(200, {'ok': True, 'msg': msg, 'name': nm})
            return self._json(401, {'ok': False, 'msg': msg})
        # ── 登出 ──
        if path == '/api/logout':
            with _lock:
                set_ctx(cid, None, None)
            return self._json(200, {'ok': True})
        # ── 会话状态（免登录模式：无 cid 会话时返回自动授权状态）──
        if path == '/api/session':
            with _lock:
                ctx = get_ctx(cid)
                auto = ctx is None
                if ctx is None:
                    ctx = ensure_auto(get_client_ip(self))
                    if ctx is None:
                        # 主账号瞬时失败 → 尝试备选账号
                        _ip = get_client_ip(self)
                        _main = pick_account(_ip)['email']
                        for _acc in ACCOUNTS:
                            if _acc['email'] != _main:
                                ctx = ensure_auto_for(_acc['email'])
                                if ctx:
                                    break
                ok = ctx is not None
                email = ctx['email'] if ctx else ''
                name = ctx['name'] if ctx else ''
            return self._json(200, {'ok': ok, 'email': email, 'name': name, 'auto': auto})
        # ── 试听/下载代理（免登录自动授权，流式转发，不落盘；失败自动换账号重试）──
        m = re.match(r'^/api/(audio|download)/(\d+)$', path)
        if m and self.command == 'GET':
            kind, tid = m.group(1), m.group(2)
            with _lock:
                uctx = get_ctx(cid)
            if uctx and uctx.get('s'):
                # 登录用户：用户会话
                r = self._stream_audio(uctx['s'], tid, kind)
                if r:
                    return r
                return self._json(502, {'ok': False, 'msg': '音频源响应异常'})
            # 免登录：主账号 → 备选账号依次尝试
            ip = get_client_ip(self)
            main_email = pick_account(ip)['email']
            emails = [main_email] + [a['email'] for a in ACCOUNTS if a['email'] != main_email]
            for email in emails:
                with _lock:
                    ctx = ensure_auto_for(email)
                    s = ctx['s'] if ctx else None
                if s is None:
                    continue
                rr = self._stream_audio(s, tid, kind)
                if rr:
                    return rr
            return self._json(502, {'ok': False, 'msg': '音频源响应异常'})
        return self._json(404, {'ok': False, 'msg': 'not found'})

    def do_GET(self):
        if self.path.startswith('/api/'):
            return self._api()
        parsed = urlparse(self.path)
        p = parsed.path
        if p == '/' or p == '':
            p = '/index.html'
        fp = os.path.normpath(os.path.join(SITE_DIR, p.lstrip('/')))
        if not fp.startswith(SITE_DIR) or not os.path.isfile(fp):
            self.send_error(404)
            return
        ext = os.path.splitext(fp)[1].lower()
        ctype = MIME.get(ext, 'application/octet-stream')
        with open(fp, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        if ext in ('.html', '.js', '.css'):
            self.send_header('Cache-Control', 'no-cache')
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _stream_audio(self, s, tid, kind):
        """尝试用某会话流式转发音频；失败返回 None，成功返回已响应结果"""
        try:
            r = proxy_stream(s, '/transload/download/' + tid, self.headers)
        except Exception:
            return None
        if r.status_code not in (200, 206):
            r.close()
            return None
        ct = r.headers.get('Content-Type', 'audio/mpeg')
        cl = r.headers.get('Content-Length')
        cr = r.headers.get('Content-Range')
        self.send_response(r.status_code)
        self.send_header('Content-Type', ct)
        self.send_header('Accept-Ranges', 'bytes')
        if cr:
            self.send_header('Content-Range', cr)
        if kind == 'download':
            self.send_header('Content-Disposition', 'attachment; filename="%s.mp3"' % tid)
        if cl:
            self.send_header('Content-Length', cl)
        self.send_header('Cache-Control', 'no-store')
        self._cors()
        self.end_headers()
        try:
            for chunk in r.iter_content(65536):
                if chunk:
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            r.close()
        return True

    def do_POST(self):
        self._api()

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()


if __name__ == '__main__':
    load_users()
    print('PandaIndex server on http://localhost:%d  (site: %s)' % (PORT, SITE_DIR))
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
