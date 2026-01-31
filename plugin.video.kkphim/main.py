# -*- coding: utf-8 -*-
import sys
import json
import urllib.request
import urllib.parse
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

# --- KHỞI TẠO ADD-ON ---
ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
URL_SCRIPT = sys.argv[0]

def get_setting(id):
    return ADDON.getSetting(id)

def set_view_mode():
    """Ép kiểu hiển thị dựa trên cài đặt người dùng"""
    view_cfg = get_setting('view_type')
    view_ids = {"1": 51, "2": 500, "3": 504, "4": 53}
    if view_cfg in view_ids:
        xbmc.executebuiltin(f"Container.SetViewMode({view_ids[view_cfg]})")

def get_data(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        xbmc.log(f"[KKPHIM_ERROR]: {str(e)}", xbmc.LOGERROR)
        return None

def add_item(label, is_folder=True, **kwargs):
    url = f"{URL_SCRIPT}?{urllib.parse.urlencode(kwargs)}"
    li = xbmcgui.ListItem(label=label)
    if 'img' in kwargs:
        li.setArt({'thumb': kwargs['img'], 'poster': kwargs['img'], 'fanart': kwargs['img']})
    if 'plot' in kwargs:
        li.setInfo('video', {'plot': kwargs['plot'], 'title': label})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, is_folder)

# --- MENU CHÍNH ---
def list_main_menu():
    xbmcplugin.setContent(HANDLE, 'movies')
    add_item("[ 🔍 TÌM KIẾM PHIM ]", action='search')
    add_item("[ 🔥 PHIM MỚI CẬP NHẬT ]", action='list_latest', page='1')
    add_item("[ 📂 XEM THEO THỂ LOẠI ]", action='browse', type='the-loai')
    add_item("[ 🌍 XEM THEO QUỐC GIA ]", action='browse', type='quoc-gia')
    add_item("[ ⚙️ CÀI ĐẶT HỆ THỐNG ]", action='open_settings', is_folder=False)
    
    try:
        history_str = get_setting('history')
        if history_str:
            history = json.loads(history_str)
            for item in history:
                add_item(f"🕒 {item['name']}", action='list_servers', slug=item['slug'])
    except: pass
    xbmcplugin.endOfDirectory(HANDLE)

# --- XỬ LÝ DANH MỤC & TÌM KIẾM ---
def list_movies(slug, page, mode, is_search=False):
    domain = get_setting('api_domain') or "https://phimapi.com"
    page = str(page)
    
    if is_search:
        url = f"{domain}/v1/api/tim-kiem?keyword={slug}&page={page}"
    elif mode == 'phim-moi-cap-nhat':
        url = f"{domain}/danh-sach/phim-moi-cap-nhat?page={page}"
    else:
        url = f"{domain}/v1/api/{mode.replace('_', '-')}/{slug}?page={page}"

    data = get_data(url)
    if data:
        if 'data' in data and 'items' in data['data']:
            res = data['data']
            items = res['items']
            cdn_base = res.get('APP_DOMAIN_CDN_IMAGE', 'https://phimimg.com').strip().rstrip('/')
        else:
            items = data.get('items', [])
            cdn_base = "https://phimimg.com"

        for m in items:
            name = m.get('name', 'N/A')
            li = xbmcgui.ListItem(label=name)
            
            # 1. Xử lý ảnh
            raw_poster = m.get('poster_url', '')
            if raw_poster:
                if raw_poster.startswith('http'): poster = raw_poster
                elif 'upload/' in raw_poster: poster = f"{cdn_base}/{raw_poster.lstrip('/')}"
                else: poster = f"{cdn_base}/upload/vod/{raw_poster.lstrip('/')}"
            else: poster = ''
            
            # 2. Xử lý thông tin bổ sung (Thể loại & Số tập)
            genres = ", ".join([g['name'] for g in m.get('category', [])])
            ep_current = m.get('episode_current', '??')
            ep_total = m.get('episode_total', '??')
            
            full_plot = f"[🔹 THỂ LOẠI]: {genres}\n"
            full_plot += f"[🔹 TÌNH TRẠNG]: {ep_current} / {ep_total}\n"
            full_plot += f"----------------------------------\n"
            full_plot += f"{m.get('content', '')}"
            
            li.setArt({'thumb': poster, 'poster': poster, 'fanart': poster})
            li.setInfo('video', {
                'title': name, 
                'year': m.get('year', ''), 
                'plot': full_plot,
                'genre': genres,
                'status': ep_current
            })
            
            url_srv = f"{URL_SCRIPT}?{urllib.parse.urlencode({'action': 'list_servers', 'slug': m['slug']})}"
            xbmcplugin.addDirectoryItem(HANDLE, url_srv, li, True)
            
        if len(items) >= 10:
            add_item(">> TRANG KẾ TIẾP", action='list_movies', mode=mode, slug=slug, page=str(int(page)+1), is_search=is_search)
    
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE)
    set_view_mode()

def list_servers(slug):
    domain = get_setting('api_domain') or "https://phimapi.com"
    data = get_data(f"{domain}/phim/{slug}")
    if not data or not data.get('status'): return

    movie = data['movie']
    poster = movie.get('poster_url', '')
    
    # Tạo plot cho server tương tự như list_movies
    genres = ", ".join([g['name'] for g in movie.get('category', [])])
    plot = f"[🔹 THỂ LOẠI]: {genres}\n"
    plot += f"[🔹 TÌNH TRẠNG]: {movie.get('episode_current')} / {movie.get('episode_total')}\n"
    plot += f"----------------------------------\n{movie.get('content', '')}"

    try:
        history = json.loads(get_setting('history') or '[]')
        history = [i for i in history if i['slug'] != slug]
        history.insert(0, {'name': movie['name'], 'slug': slug})
        ADDON.setSetting('history', json.dumps(history[:10]))
    except: pass

    servers = data.get('episodes', [])
    if len(servers) > 1:
        for idx, srv in enumerate(servers):
            srv_label = f"[COLOR yellow]▶ {srv.get('server_name', 'Server')}[/COLOR]"
            add_item(srv_label, action='list_episodes', slug=slug, srv_idx=str(idx), img=poster, plot=plot)
        xbmcplugin.endOfDirectory(HANDLE)
    else:
        list_episodes(slug, srv_idx='0')

def list_episodes(slug, srv_idx='0', range_idx=None):
    domain = get_setting('api_domain') or "https://phimapi.com"
    data = get_data(f"{domain}/phim/{slug}")
    if not data: return

    movie = data['movie']
    poster = movie.get('poster_url', '')
    genres = ", ".join([g['name'] for g in movie.get('category', [])])
    plot = f"[🔹 THỂ LOẠI]: {genres}\n"
    plot += f"[🔹 TÌNH TRẠNG]: {movie.get('episode_current')} / {movie.get('episode_total')}\n"
    plot += f"----------------------------------\n{movie.get('content', '')}"
    
    try:
        server_data = data['episodes'][int(srv_idx)]['server_data']
    except: return

    total = len(server_data)
    idx_cfg = get_setting('ep_per_page')
    steps = [25, 50, 75, 100]
    step = steps[int(idx_cfg)] if (idx_cfg and idx_cfg.isdigit()) else 50

    if total > step and range_idx is None:
        for i in range(0, total, step):
            label = f">> Danh sách tập {i+1} - {min(i+step, total)}"
            add_item(label, action='list_episodes', slug=slug, srv_idx=srv_idx, range_idx=str(i), img=poster, plot=plot)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    start = int(range_idx) if range_idx else 0
    for ep in server_data[start : start + step]:
        display_name = ep.get('filename') or ep.get('name')
        li = xbmcgui.ListItem(label=display_name)
        li.setArt({'thumb': poster, 'poster': poster, 'fanart': poster})
        li.setInfo('video', {'title': display_name, 'plot': plot})
        li.setProperty('IsPlayable', 'true')
        li.setProperty('inputstream', 'inputstream.adaptive')
        li.setProperty('inputstream.adaptive.manifest_type', 'hls')
        xbmcplugin.addDirectoryItem(HANDLE, ep['link_m3u8'], li, False)
    
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)

if __name__ == '__main__':
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
    action = params.get('action')
    
    if action == 'search':
        kb = xbmc.Keyboard('', 'Tìm kiếm phim...')
        kb.doModal()
        if kb.isConfirmed() and kb.getText():
            list_movies(urllib.parse.quote_plus(kb.getText()), '1', '', is_search=True)
    elif action == 'list_latest': 
        list_movies('', params.get('page', '1'), 'phim-moi-cap-nhat')
    elif action == 'browse':
        api_type = params.get('type')
        domain = get_setting('api_domain') or "https://phimapi.com"
        data = get_data(f"{domain}/{api_type}")
        if data:
            items = data if isinstance(data, list) else data.get('items', [])
            for item in items:
                add_item(item['name'], action='list_movies', mode=api_type, slug=item['slug'], page='1')
        xbmcplugin.endOfDirectory(HANDLE)
    elif action == 'list_movies': 
        list_movies(params.get('slug'), params.get('page', '1'), params.get('mode'), params.get('is_search') == 'True')
    elif action == 'list_servers': 
        list_servers(params.get('slug'))
    elif action == 'list_episodes': 
        list_episodes(params.get('slug'), params.get('srv_idx', '0'), params.get('range_idx'))
    elif action == 'open_settings': 
        ADDON.openSettings()
    else: 
        list_main_menu()
