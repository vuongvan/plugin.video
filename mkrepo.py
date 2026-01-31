# -*- coding: utf-8 -*-
import os
import hashlib
import zipfile
import xml.etree.ElementTree as ET

def generate_md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def create_html_index(path, title, items, is_sub=False):
    """Tạo file index.html để Kodi duyệt được file"""
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Index of {title}</title>
    <style>
        body {{ background-color: #121212; color: #e0e0e0; font-family: sans-serif; padding: 20px; }}
        a {{ color: #81d4fa; text-decoration: none; font-size: 1.1em; line-height: 2; display: block; }}
        a:hover {{ color: #00e676; text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>Index of {title}</h1>
    <hr><pre>
    {'<a href="../">../ (Thư mục cha)</a>' if is_sub else ''}
    {''.join([f'<a href="{i}">{i}</a>' for i in items])}
    </pre><hr>
</body>
</html>"""
    with open(os.path.join(path, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

def create_kodi_repo():
    addons_xml = ET.Element("addons")
    subdirs = [d for d in os.listdir('.') if os.path.isdir(d) and os.path.exists(os.path.join(d, 'addon.xml'))]
    
    # Danh sách để làm index cho thư mục gốc
    root_index_items = ["addons.xml", "addons.xml.md5"]

    for addon_id in subdirs:
        if addon_id.startswith('.') or addon_id == 'publish': continue
        
        xml_path = os.path.join(addon_id, 'addon.xml')
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            addons_xml.append(root)
            
            version = root.get('version')
            addon_id_xml = root.get('id')
            root_index_items.append(f"{addon_id}/") # Thêm vào index gốc

            # Xử lý file ZIP
            existing_zip = next((f for f in os.listdir(addon_id) if f.endswith('.zip') and version in f), None)
            if not existing_zip:
                zip_name = f"{addon_id_xml}-{version}.zip"
                zip_path = os.path.join(addon_id, zip_name)
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for r, d, files in os.walk(addon_id):
                        for file in files:
                            if not file.endswith('.zip') and not file.endswith('.html'):
                                f_path = os.path.join(r, file)
                                arcname = os.path.join(addon_id_xml, os.path.relpath(f_path, addon_id))
                                zipf.write(f_path, arcname)
            
            # Tạo index cho thư mục con (addon)
            addon_files = [f for f in os.listdir(addon_id) if not f.endswith('.html')]
            create_html_index(addon_id, f"/{addon_id}/", addon_files, is_sub=True)
                                
        except Exception as e:
            print(f"❌ Lỗi {addon_id}: {e}")

    # Tạo addons.xml & md5
    ET.ElementTree(addons_xml).write("addons.xml", encoding="utf-8", xml_declaration=True)
    with open("addons.xml.md5", "w") as f: f.write(generate_md5("addons.xml"))
    
    # Tạo index cho thư mục gốc
    create_html_index(".", "/", root_index_items)

if __name__ == "__main__":
    create_kodi_repo()
