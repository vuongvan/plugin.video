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

def create_kodi_repo():
    addons_xml = ET.Element("addons")
    # Quét tất cả thư mục có chứa addon.xml
    subdirs = [d for d in os.listdir('.') if os.path.isdir(d) and os.path.exists(os.path.join(d, 'addon.xml'))]

    print("🚀 Bắt đầu quét các addon...")

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
            
            # Kiểm tra xem có file zip sẵn (đúng id và version) không
            existing_zip = None
            for f in os.listdir(addon_id):
                if f.endswith('.zip') and version in f:
                    existing_zip = f
                    break
            
            if existing_zip:
                print(f"✔️ Dùng ZIP có sẵn: {addon_id} ({existing_zip})")
            else:
                zip_name = f"{addon_id_xml}-{version}.zip"
                zip_path = os.path.join(addon_id, zip_name)
                print(f"📦 Đang nén mới: {addon_id} (v{version})")
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root_dir, dirs, files in os.walk(addon_id):
                        for file in files:
                            if not file.endswith('.zip'):
                                file_path = os.path.join(root_dir, file)
                                # Cấu trúc chuẩn: ID-Addon/tên-file
                                arcname = os.path.join(addon_id_xml, os.path.relpath(file_path, addon_id))
                                zipf.write(file_path, arcname)
                                
        except Exception as e:
            print(f"❌ Lỗi xử lý {addon_id}: {str(e)}")

    # Tạo file addons.xml tổng hợp
    indent(addons_xml)
    tree_main = ET.ElementTree(addons_xml)
    tree_main.write("addons.xml", encoding="utf-8", xml_declaration=True)
    
    # Tạo mã MD5
    with open("addons.xml.md5", "w") as f:
        f.write(generate_md5("addons.xml"))
    
    print("\n✅ HOÀN TẤT!")

if __name__ == "__main__":
    create_kodi_repo()
    
