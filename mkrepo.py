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

def create_kodi_repo():
    addons_xml = ET.Element("addons")
    # Tìm các thư mục bắt đầu bằng plugin. hoặc repository.
    subdirs = [d for d in os.listdir('.') if os.path.isdir(d) and (d.startswith('plugin.') or d.startswith('repository.'))]

    for addon_id in subdirs:
        xml_path = os.path.join(addon_id, 'addon.xml')
        if not os.path.exists(xml_path):
            continue

        # Đọc nội dung addon.xml để gộp vào file tổng
        tree = ET.parse(xml_path)
        root = tree.getroot()
        addons_xml.append(root)
        
        version = root.get('version')
        zip_name = f"{addon_id}-{version}.zip"
        zip_path = os.path.join(addon_id, zip_name)

        # Nén thư mục thành file ZIP chuẩn Kodi
        print(f"Bắt đầu nén: {zip_path}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root_dir, dirs, files in os.walk(addon_id):
                for file in files:
                    if not file.endswith('.zip'): # Không nén chính nó
                        file_path = os.path.join(root_dir, file)
                        # Đảm bảo cấu trúc trong zip có thư mục mẹ
                        arcname = os.path.relpath(file_path, os.path.join(addon_id, '..'))
                        zipf.write(file_path, arcname)

    # Xuất file addons.xml tổng
    indent(addons_xml)
    tree_main = ET.ElementTree(addons_xml)
    tree_main.write("addons.xml", encoding="utf-8", xml_declaration=True)
    
    # Tạo mã MD5 cho file addons.xml
    with open("addons.xml.md5", "w") as f:
        f.write(generate_md5("addons.xml"))
    print("Hoàn tất: Đã tạo xong addons.xml và addons.xml.md5")

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

if __name__ == "__main__":
    create_kodi_repo()
