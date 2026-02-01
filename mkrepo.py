# -*- coding: utf-8 -*-
import os
import hashlib
import zipfile
import xml.etree.ElementTree as ET

def generate_md5(fname):
    """Tạo mã MD5 để Kodi kiểm tra cập nhật"""
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def create_html_index(path, title, items, is_sub=False):
    """Tạo giao diện liệt kê file để Kodi File Manager có thể đọc được"""
    links = ['<a href="../">../</a>'] if is_sub else []
    for item in items:
        # Đảm bảo thư mục có dấu / ở cuối để Kodi hiểu
        links.append(f'<a href="{item}">{item}</a>')
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Index of {title}</title>
    <style>
        body {{ background-color: #121212; color: #e0e0e0; font-family: sans-serif; padding: 20px; }}
        a {{ color: #81d4fa; text-decoration: none; font-size: 1.1em; line-height: 2; display: block; }}
        a:hover {{ color: #00e676; text-decoration: underline; }}
    </pre></head>
<body>
    <h1>Index of {title}</h1>
    <hr><pre>
{chr(10).join(links)}
    </pre><hr>
</body>
</html>"""
    with open(os.path.join(path, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

def create_kodi_repo():
    addons_xml = ET.Element("addons")
    # Tìm các thư mục có chứa file addon.xml
    subdirs = [d for d in os.listdir('.') if os.path.isdir(d) and os.path.exists(os.path.join(d, 'addon.xml'))]
    
    root_index_items = ["addons.xml", "addons.xml.md5"]

    for addon_id in subdirs:
        if addon_id.startswith('.') or addon_id == 'publish':
            continue
        
        xml_path = os.path.join(addon_id, 'addon.xml')
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            addons_xml.append(root)
            
            version = root.get('version')
            addon_id_xml = root.get('id')
            
            # 1. Kiểm tra xem đã có file ZIP đúng phiên bản chưa
            existing_zip = next((f for f in os.listdir(addon_id) if f.endswith('.zip') and version in f), None)
            
            if not existing_zip:
                zip_name = f"{addon_id_xml}-{version}.zip"
                zip_path = os.path.join(addon_id, zip_name)
                print(f"📦 Đang nén mới: {zip_name}")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for r, d, files in os.walk(addon_id):
                        for file in files:
                            # KHÔNG nén các file zip cũ, file html hoặc file ẩn
                            if not file.endswith('.zip') and not file.endswith('.html') and not file.startswith('.'):
                                f_path = os.path.join(r, file)
                                arcname = os.path.join(addon_id_xml, os.path.relpath(f_path, addon_id))
                                zipf.write(f_path, arcname)
            else:
                print(f"✔️ Đã có sẵn ZIP: {existing_zip}")
            
            # 2. Tạo danh sách file để hiện trong thư mục con (chỉ lấy ZIP, PNG, XML)
            addon_dir_content = [f for f in os.listdir(addon_id) if f.endswith(('.zip', '.xml', '.png', '.jpg'))]
            create_html_index(addon_id, f"/{addon_id}/", addon_dir_content, is_sub=True)
            
            # 3. Thêm tên thư mục vào danh sách trang chủ
            root_index_items.append(f"{addon_id}/")
                                
        except Exception as e:
            print(f"❌ Lỗi xử lý addon {addon_id}: {e}")

    # Tạo file addons.xml tổng hợp
    ET.indent(addons_xml, space="  ", level=0)
    tree_main = ET.ElementTree(addons_xml)
    tree_main.write("addons.xml", encoding="utf-8", xml_declaration=True)
    
    # Tạo file MD5
    with open("addons.xml.md5", "w") as f:
        f.write(generate_md5("addons.xml"))
    
    # Tạo file index.html cho trang chủ
    create_html_index(".", "/", root_index_items)
    print("✅ Hoàn tất build Repository!")

if __name__ == "__main__":
    create_kodi_repo()
        
