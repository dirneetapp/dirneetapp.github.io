#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bar Sergio's - Firestore to Web Static Synchronizer
Descarga todos los platos, órdenes y fotos de Firestore (App Admin)
y actualiza menu.json, assets y todos los archivos .html estáticos.
"""

import urllib.request
import json
import base64
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MENU_JSON_PATH = os.path.join(BASE_DIR, 'menu.json')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

CATEGORY_MAP = {
    'DESAYUNOS': 'Desayunos',
    'BOCADILLOS': 'Bocadillos',
    'VERMUTS': 'Vermuts',
    'TAPAS': 'Tapas',
    'TORRADAS': 'Torradas',
    'TABLAS': 'Tablas',
    'PLATOS_ESPECIALES': 'Platos Especiales',
    'ARROZ': 'Tapa de Arroz',
    'CROQUETAS': 'Croquetas',
    'POSTRES': 'Postres'
}

FIRESTORE_URL = "https://firestore.googleapis.com/v1/projects/bar-sergios-fidelizacion/databases/(default)/documents/menu?pageSize=300"

def fetch_firestore_menu():
    print("📡 Conectando a Firebase Firestore para descargar la carta...")
    req = urllib.request.Request(FIRESTORE_URL, headers={'User-Agent': 'BarSergiosSync/1.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    
    docs = data.get('documents', [])
    print(f"✅ Se han obtenido {len(docs)} platos desde Firestore.")
    
    items_by_cat = {}
    for doc in docs:
        fields = doc.get('fields', {})
        doc_id = doc['name'].split('/')[-1]
        
        cat_key = fields.get('category', {}).get('stringValue', 'TAPAS')
        name = fields.get('name', {}).get('stringValue', '').strip()
        desc = fields.get('description', {}).get('stringValue', '').strip()
        
        # Precio
        price_val = 0.0
        if 'price' in fields:
            p_dict = fields['price']
            if 'doubleValue' in p_dict:
                price_val = float(p_dict['doubleValue'])
            elif 'integerValue' in p_dict:
                price_val = float(p_dict['integerValue'])
        
        # Orden
        order_val = 0
        if 'order' in fields:
            o_dict = fields['order']
            if 'integerValue' in o_dict:
                order_val = int(o_dict['integerValue'])
            elif 'doubleValue' in o_dict:
                order_val = int(float(o_dict['doubleValue']))
        
        is_avail = fields.get('isAvailable', {}).get('booleanValue', True)
        is_stock = fields.get('isOutOfStock', {}).get('booleanValue', False)
        is_popular = fields.get('isPopular', {}).get('booleanValue', False)
        is_new = fields.get('isNew', {}).get('booleanValue', False)
        emoji = fields.get('iconEmoji', {}).get('stringValue', '').strip()
        spice_level = int(fields.get('spiceLevel', {}).get('integerValue', 0))
        
        # Alérgenos
        allergens_list = []
        if 'allergens' in fields and 'arrayValue' in fields['allergens']:
            values = fields['allergens']['arrayValue'].get('values', [])
            allergens_list = [v.get('stringValue', '').lower() for v in values if 'stringValue' in v]
        
        # Imagen Base64
        b64_str = fields.get('imageBase64', {}).get('stringValue', '').strip()
        image_path = ""
        if len(b64_str) > 100:
            clean_b64 = b64_str.split(',', 1)[1] if ',' in b64_str else b64_str
            try:
                img_bytes = base64.b64decode(clean_b64)
                img_filename = f"{doc_id}.jpg"
                full_img_path = os.path.join(ASSETS_DIR, img_filename)
                with open(full_img_path, 'wb') as img_f:
                    img_f.write(img_bytes)
                image_path = f"assets/{img_filename}"
                print(f"  📷 Foto guardada: {image_path} ({len(img_bytes)} bytes) para '{name}'")
                
                # Caso especial Coulant: también actualizar item_Coulant.webp si existe
                if 'coulant' in name.lower() or doc_id == 'item_postres_167':
                    coulant_webp = os.path.join(ASSETS_DIR, 'item_Coulant.webp')
                    with open(coulant_webp, 'wb') as cw:
                        cw.write(img_bytes)
                    print(f"  🍮 Foto de Coulant replicada en {coulant_webp}")
            except Exception as e:
                print(f"  ⚠️ Error guardando foto de {name}: {e}")
        
        if not is_avail:
            # Plato desactivado en Admin, omitir de la carta web activa
            continue
            
        item_obj = {
            'firestore_id': doc_id,
            'name': name,
            'description': desc,
            'price': price_val,
            'order': order_val,
            'is_stock': is_stock,
            'is_popular': is_popular,
            'is_new': is_new,
            'emoji': emoji,
            'spice_level': spice_level,
            'allergens': allergens_list,
            'image_path': image_path
        }
        
        items_by_cat.setdefault(cat_key, []).append(item_obj)
        
    return items_by_cat

def update_menu_json(firestore_items):
    print("📝 Actualizando menu.json con los datos y orden de Firestore...")
    with open(MENU_JSON_PATH, 'r', encoding='utf-8') as f:
        menu_data = json.load(f)
        
    for cat_dict in menu_data.get('categories', []):
        cat_name = cat_dict.get('name')
        
        # Buscar la clave en CATEGORY_MAP
        fs_key = None
        for k, v in CATEGORY_MAP.items():
            if v.lower() == cat_name.lower():
                fs_key = k
                break
                
        if not fs_key or fs_key not in firestore_items:
            continue
            
        fs_list = firestore_items[fs_key]
        # Ordenar por order estrictamente
        fs_list.sort(key=lambda x: x['order'])
        
        # Crear diccionario de items existentes en menu.json por nombre normalizado
        def norm(s):
            import unicodedata
            if not s: return ""
            s = s.lower().strip()
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
            
        existing_items = cat_dict.get('items', [])
        existing_by_norm = {norm(it.get('name', '')): it for it in existing_items}
        
        new_items_list = []
        for fs_item in fs_list:
            n = norm(fs_item['name'])
            existing = existing_by_norm.get(n)
            
            if existing:
                item_entry = existing.copy()
            else:
                item_entry = {
                    'id': fs_item['name'].replace("'", "").replace('"', '').replace(' ', '_'),
                    'name': fs_item['name']
                }
                
            item_entry['name'] = fs_item['name']
            item_entry['description'] = fs_item['description']
            item_entry['price'] = round(fs_item['price'], 2)
            item_entry['hidden'] = fs_item['is_stock']
            item_entry['order'] = fs_item['order']
            item_entry['tag_recomendado'] = fs_item['is_popular']
            item_entry['tag_novedad'] = fs_item['is_new']
            item_entry['spice_level'] = fs_item['spice_level']
            
            # Alérgenos
            for alg in ['gluten', 'crustaceos', 'huevos', 'pescado', 'cacahuetes', 'soja', 'lacteos', 
                        'frutos_cascara', 'apio', 'mostaza', 'sesamo', 'sulfitos', 'altramuces', 'moluscos', 'vegano']:
                item_entry[alg] = (alg in fs_item['allergens'])
                
            # Foto
            if fs_item['image_path']:
                item_entry['image'] = fs_item['image_path']
            elif 'image' not in item_entry and not fs_item['image_path']:
                # Sin imagen
                item_entry.pop('image', None)
                
            new_items_list.append(item_entry)
            
        cat_dict['items'] = new_items_list
        print(f"  ✨ Categoría '{cat_name}': {len(new_items_list)} platos ordenados sincronizados.")
        
    with open(MENU_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(menu_data, f, ensure_ascii=False, indent=2)
    print("✅ menu.json guardado con éxito.")

def regenerate_html_files():
    print("🔄 Regenerando archivos HTML estáticos (.html)...")
    os.chdir(BASE_DIR)
    sys.path.insert(0, BASE_DIR)
    from regen_html import HeadlessMenuApp
    app = HeadlessMenuApp()
    app.regenerate_html()
    print("✅ Todos los archivos HTML han sido regenerados con los platos, orden y fotos actualizadas.")

if __name__ == '__main__':
    try:
        firestore_items = fetch_firestore_menu()
        update_menu_json(firestore_items)
        print("\n🎉 SINCRONIZACIÓN DE FOTOS Y DATOS COMPLETADA CON ÉXITO.")
        print("💡 La web se sincroniza en vivo en tiempo real a través de firebase-sync.js con UTF-8 limpio.")
    except Exception as e:
        print(f"\n❌ Error durante la sincronización: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
