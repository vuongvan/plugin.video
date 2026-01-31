import sys, urllib.parse, urllib.request, json, os, re
import xbmcgui, xbmcplugin, xbmcaddon, xbmc

# Khởi tạo Addon
ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def get_setting(id): return ADDON.getSetting(id)
def set_setting(id, value): ADDON.setSetting(id, value)
def get_url(**kwargs): return sys.argv[0] + '?' + urllib.parse.urlencode(kwargs)

def get_data(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except:
        return {}

def get_image(item):
    try:
        img_path = item.get('thumb_url', '') or item.get('poster_url', '')
        if img_path:
            if img_path.startswith('http'):
                filename = img_path.split('/')[-1]
                return f"https://img.ophim.live/uploads/movies/{filename}"
            clean_path = img_path.lstrip('/')
            if 'uploads/' not in clean_path:
                return f"https://img.ophim.live/uploads/movies/{clean_path}"
            return f"https://img.ophim.live/{clean_path}"
        slug = item.get('slug', '')
        if slug: return f"https://img.ophim.live/uploads/movies/{slug}-thumb.jpg"
    except:
        pass
    return ""

# --- Các hàm chức năng chính ---

def main_menu():
    add_directory_item("[COLOR yellow]🔍 TÌM KIẾM[/COLOR]", get_url(action='search'))
    add_directory_item("[COLOR lime]🎬 PHIM MỚI CẬP NHẬT[/COLOR]", get_url(action='list_movies', category='phim-moi-cap-nhat', type='danh-sach', page=1))
    add_directory_item("[COLOR orange]🌍 XEM THEO QUỐC GIA[/COLOR]", get_url(action='list_countries'))
    add_directory_item("[COLOR cyan]📁 XEM THEO THỂ LOẠI[/COLOR]", get_url(action='list_genres'))
    add_directory_item("[COLOR gray]🕒 LỊCH SỬ XEM[/COLOR]", get_url(action='show_history'))
    xbmcplugin.endOfDirectory(HANDLE)

def list_movies(category='phim-moi-cap-nhat', page=1, query='', type='danh-sach'):
    domain = get_setting('api_domain')
    page = int(page)
    limit = 40
    url = f"{domain}/v1/api/tim-kiem?keyword={urllib.parse.quote(query)}&page={page}&limit={limit}" if query else f"{domain}/v1/api/{type}/{category}?page={page}&limit={limit}"
    resp = get_data(url)
    items = resp.get('data', {}).get('items', [])
    xbmcplugin.setContent(HANDLE, 'movies')
    for item in items:
        m_name = item.get('name')
        m_slug = item.get('slug')
        thumb = get_image(item)
        cm = [('Xuất file STRM cho TV Show', f"RunPlugin({get_url(action='export_strm', slug=m_slug, name=m_name)})")]
        add_directory_item(m_name, get_url(action='movie_detail', slug=m_slug), thumb, context_menu=cm)
    
    pagination = resp.get('data', {}).get('params', {}).get('pagination', {})
    total_items = int(pagination.get('totalItems', 0))
    if page < (total_items + limit - 1) // limit:
        add_directory_item(f"[COLOR yellow]>> TRANG {page+1} >>[/COLOR]", get_url(action='list_movies', category=category, page=page+1, query=query, type=type))
    xbmcplugin.endOfDirectory(HANDLE)

def movie_detail(slug):
    domain = get_setting('api_domain')
    data = get_data(f"{domain}/v1/api/phim/{slug}")
    item = data.get('data', {}).get('item', {})
    if not item: return
    poster = get_image(item)
    save_history(item.get('name'), slug, poster)
    xbmcplugin.setContent(HANDLE, 'episodes')
    
    try:
        mapping = {"0": 25, "1": 50, "2": 75, "3": 100}
        group_size = mapping.get(get_setting('ep_per_page'), 50)
    except:
        group_size = 50

    for s_idx, server in enumerate(item.get('episodes', [])):
        data_eps = server.get('server_data', [])
        if len(data_eps) > group_size:
            for i in range(0, len(data_eps), group_size):
                end = min(i + group_size, len(data_eps))
                add_directory_item(f"[{server.get('server_name')}] Tập {i+1} - {end}", get_url(action='list_episodes', slug=slug, s_idx=s_idx, start=i, end=end), poster)
        else:
            for ep in data_eps:
                add_episode_item(f"[{server.get('server_name')}] {ep.get('filename', ep.get('name'))}", ep['link_m3u8'], item, poster)
    xbmcplugin.endOfDirectory(HANDLE)

def list_episodes(slug, s_idx, start, end):
    data = get_data(f"{get_setting('api_domain')}/v1/api/phim/{slug}")
    item = data.get('data', {}).get('item', {})
    server = item.get('episodes', [])[int(s_idx)]
    data_eps = server.get('server_data', [])[int(start):int(end)]
    xbmcplugin.setContent(HANDLE, 'episodes')
    poster = get_image(item)
    for ep in data_eps:
        add_episode_item(f"[{server.get('server_name')}] {ep.get('filename', ep.get('name'))}", ep['link_m3u8'], item, poster)
    xbmcplugin.endOfDirectory(HANDLE)

def export_strm(slug, name):
    path = get_setting('strm_path')
    if not path:
        xbmcgui.Dialog().ok("Lỗi", "Vui lòng chọn thư mục lưu trong cài đặt Addon")
        return
        
    # Lấy dữ liệu từ API
    url_api = f"{get_setting('api_domain')}/v1/api/phim/{slug}"
    resp = get_data(url_api)
    
    # Theo cấu trúc API bạn gửi, dữ liệu thực tế nằm trong resp['data']['item']
    # Hoặc đôi khi là resp['data']['movie']
    data_content = resp.get('data', {})
    item = data_content.get('item', {})
    
    if not item:
        # Dự phòng nếu API trả về cấu trúc khác
        item = data_content.get('movie', {})
    
    if not item: return

    # 1. Tạo thư mục
    clean_name = re.sub(r'[\\/*?:"<>|]', '', name)
    folder = os.path.join(path, clean_name)
    if not os.path.exists(folder):
        try: os.makedirs(folder)
        except: return

    # 2. Bóc tách ID - Kiểm tra kỹ các trường tmdb, imdb
    # Trong API OPhim v1: các trường này thường nằm ở item['tmdb']['id'] hoặc item['movie']['tmdb']['id']
    
    tmdb_id = ""
    imdb_id = ""
    
    # Thử lấy tmdb id (có thể là chuỗi hoặc đối tượng dict)
    tmdb_data = item.get('tmdb', {})
    if isinstance(tmdb_data, dict):
        tmdb_id = tmdb_data.get('id', '')
    else:
        tmdb_id = item.get('tmdb_id', '')

    # Thử lấy imdb id
    imdb_data = item.get('imdb', {})
    if isinstance(imdb_data, dict):
        imdb_id = imdb_data.get('id', '')
    else:
        imdb_id = item.get('imdb_id', '')

    # 3. Tạo nội dung XML NFO chuẩn
    nfo_content = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'
    nfo_content += '<tvshow>\n'
    nfo_content += f'    <title>{name}</title>\n'
    
    # Ghi ID vào thẻ uniqueid để Kodi nhận diện 100%
    if imdb_id and str(imdb_id).lower() != 'null':
        nfo_content += f'    <uniqueid type="imdb" default="true">{imdb_id}</uniqueid>\n'
    
    if tmdb_id and str(tmdb_id).lower() != 'null':
        # Nếu chưa có imdb thì tmdb làm mặc định
        is_default = 'true' if not imdb_id else 'false'
        nfo_content += f'    <uniqueid type="tmdb" default="{is_default}">{tmdb_id}</uniqueid>\n'
    
    nfo_content += '</tvshow>'

    # Ghi file tvshow.nfo
    nfo_path = os.path.join(folder, "tvshow.nfo")
    try:
        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
    except Exception as e:
        xbmc.log(f"DEBUG_NFO_ERROR: {str(e)}", xbmc.LOGERROR)

    # 4. Xuất các tập phim .strm (Lấy server đầu tiên)
    count = 0
    episodes_list = item.get('episodes', [])
    if episodes_list:
        server_data = episodes_list[0].get('server_data', [])
        for ep in server_data:
            ep_num = ep.get('name', '')
            formatted_ep = ep_num.zfill(2) if ep_num.isdigit() else ep_num
            f_name = f"S01E{formatted_ep}.strm"
            
            try:
                with open(os.path.join(folder, f_name), 'w', encoding='utf-8') as f:
                    f.write(ep.get('link_m3u8'))
                count += 1
            except: pass
            
    xbmcgui.Dialog().notification("STRM", f"Đã tạo {clean_name} với ID: {tmdb_id}")

# --- Các hàm phụ trợ ---

def add_directory_item(name, url, thumb='', is_folder=True, context_menu=None):
    li = xbmcgui.ListItem(label=name)
    if thumb: li.setArt({'thumb': thumb, 'icon': thumb, 'fanart': thumb})
    if context_menu: li.addContextMenuItems(context_menu)
    xbmcplugin.addDirectoryItem(HANDLE, url, li, is_folder)

def add_episode_item(name, link, movie, thumb):
    li = xbmcgui.ListItem(label=name)
    li.setArt({'thumb': thumb, 'icon': thumb, 'fanart': thumb})
    li.setInfo('video', {'plot': movie.get('content',''), 'title': name, 'mediatype': 'episode'})
    li.setProperty('IsPlayable', 'false' if get_setting('use_external_player') == 'true' else 'true')
    xbmcplugin.addDirectoryItem(HANDLE, link, li, False)

def save_history(title, slug, thumb):
    try:
        h = json.loads(get_setting('history') or '[]')
        h = [i for i in h if i.get('slug') != slug]
        h.insert(0, {'title': title, 'slug': slug, 'thumb': thumb})
        set_setting('history', json.dumps(h[:20]))
    except:
        pass

def show_history():
    add_directory_item("[COLOR red]❌ XÓA LỊCH SỬ[/COLOR]", get_url(action='clear_history'))
    try:
        history_list = json.loads(get_setting('history') or '[]')
        for item in history_list:
            add_directory_item(f"🕒 {item['title']}", get_url(action='movie_detail', slug=item['slug']), item['thumb'])
    except:
        pass
    xbmcplugin.endOfDirectory(HANDLE)

def list_countries():
    resp = get_data(f"{get_setting('api_domain')}/v1/api/quoc-gia")
    for i in resp.get('data', {}).get('items', []):
        add_directory_item(i['name'], get_url(action='list_movies', category=i['slug'], type='quoc-gia', page=1))
    xbmcplugin.endOfDirectory(HANDLE)

def list_genres():
    resp = get_data(f"{get_setting('api_domain')}/v1/api/the-loai")
    for i in resp.get('data', {}).get('items', []):
        add_directory_item(i['name'], get_url(action='list_movies', category=i['slug'], type='the-loai', page=1))
    xbmcplugin.endOfDirectory(HANDLE)

def search():
    q = xbmcgui.Dialog().input('Tìm phim...', type=xbmcgui.INPUT_ALPHANUM)
    if q: list_movies(query=q, page=1)

# --- Router ---
params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
act = params.get('action')
if not act:
    main_menu()
elif act == 'list_movies':
    list_movies(params.get('category'), params.get('page', 1), params.get('query', ''), params.get('type', 'danh-sach'))
elif act == 'movie_detail':
    movie_detail(params.get('slug'))
elif act == 'list_episodes':
    list_episodes(params['slug'], params['s_idx'], params['start'], params['end'])
elif act == 'export_strm':
    export_strm(params['slug'], params['name'])
elif act == 'list_countries':
    list_countries()
elif act == 'list_genres':
    list_genres()
elif act == 'search':
    search()
elif act == 'show_history':
    show_history()
elif act == 'clear_history':
    set_setting('history', '[]')
    xbmc.executebuiltin("Container.Refresh")
    