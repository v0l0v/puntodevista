#!/usr/bin/env python3
"""
museum_archive.py — Conector Unificado con la Red de Museos y Fondos Internacionales de Fotografía.
Combina:
  1. APIs abiertas en vivo: Victoria & Albert Museum (Londres) y The Metropolitan Museum of Art (Nueva York).
  2. Fondos históricos curados: Center for Creative Photography (Tucson), Musée Nicéphore-Niépce (Chalon),
     Gernsheim Collection (Austin, Texas), MEP (París), Centre Pompidou y MFA Boston/Cincinnati.
"""

import json
import os
import random
import re
import requests
import logging

from config import ensure_warp_proxy
from data_paths import get_data_path

logger = logging.getLogger('pdv.museum')
MASTERS_PATH = get_data_path('museum_curated_masters.json')

VA_SEARCH_URL = 'https://api.vam.ac.uk/v2/objects/search'
VA_OBJECT_URL = 'https://api.vam.ac.uk/v2/object/'

MET_SEARCH_URL = 'https://collectionapi.metmuseum.org/public/collection/v1/search'
MET_OBJECT_URL = 'https://collectionapi.metmuseum.org/public/collection/v1/objects/'


def load_curated_masters():
    """Carga los fondos de instituciones sin API pública tradicional."""
    if os.path.exists(MASTERS_PATH):
        try:
            with open(MASTERS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error cargando museum_curated_masters.json: {e}")
    return []


def search_curated_masters(keywords=None):
    """Busca coincidencias temáticas en los fondos curados de Tucson, Niépce, Gernsheim, MEP, Pompidou, etc."""
    masters = load_curated_masters()
    if not masters:
        return []

    if not keywords:
        return masters

    if isinstance(keywords, str):
        kw_list = re.findall(r'\b\w{3,}\b', keywords.lower())
    else:
        kw_list = [str(k).lower() for k in keywords]

    matches = []
    for m in masters:
        score = 0
        tags = [t.lower() for t in m.get('tags', [])]
        text_blob = (m.get('title', '') + ' ' + m.get('photographer', '') + ' ' + m.get('curatorial_notes', '')).lower()
        for kw in kw_list:
            if kw in tags:
                score += 3
            elif kw in text_blob:
                score += 1
        if score > 0:
            matches.append((score, m))

    matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matches] if matches else masters


def search_va_photographs(query='landscape', limit=3):
    """Busca fotografías en la colección abierta del Victoria & Albert Museum (Londres)."""
    ensure_warp_proxy()
    q_str = f"photograph {query}".strip()
    params = {
        'q': q_str,
        'images_exist': 1,
        'page_size': limit * 2
    }
    try:
        resp = requests.get(VA_SEARCH_URL, params=params, timeout=12)
        if resp.status_code != 200:
            return []
        data = resp.json()
        records = data.get('records', [])
        results = []
        for rec in records:
            obj_type = (rec.get('objectType') or '').lower()
            if 'photo' not in obj_type and 'daguerreotype' not in obj_type and 'print' not in obj_type:
                continue

            sys_num = rec.get('systemNumber')
            img_id = rec.get('_primaryImageId')
            maker = rec.get('_primaryMaker', {}).get('name') or 'Autor no documentado'
            title = rec.get('_primaryTitle') or rec.get('objectType') or 'Fotografía sin título'
            date_str = rec.get('_primaryDate') or 'Sin fecha documentada'
            
            summary = ""
            technique = ""
            try:
                r_det = requests.get(f"{VA_OBJECT_URL}{sys_num}", timeout=8)
                if r_det.status_code == 200:
                    d_rec = r_det.json().get('record', {})
                    summary = d_rec.get('summaryDescription') or d_rec.get('physicalDescription') or ""
                    technique = d_rec.get('materialsAndTechniquesDescription') or ""
            except Exception:
                pass

            img_url = f"https://framemark.vam.ac.uk/collections/{img_id}/full/!800,800/0/default.jpg" if img_id else ""
            
            results.append({
                'source': 'va_museum',
                'institution': 'Victoria and Albert Museum, Londres',
                'object_id': sys_num,
                'title': title,
                'photographer': maker,
                'date': date_str,
                'technique': technique,
                'curatorial_notes': summary.strip(),
                'image_url': img_url,
                'museum_url': f"https://collections.vam.ac.uk/item/{sys_num}"
            })
            if len(results) >= limit:
                break
        return results
    except Exception as e:
        logger.warning(f"Error consultando V&A API: {e}")
        return []


def search_met_photographs(query='landscape', limit=3):
    """Busca fotografías en la colección abierta de The Met (Nueva York)."""
    ensure_warp_proxy()
    params = {
        'departmentId': 19,
        'q': query,
        'hasImages': 'true'
    }
    try:
        resp = requests.get(MET_SEARCH_URL, params=params, timeout=12)
        if resp.status_code != 200:
            return []
        data = resp.json()
        ids = data.get('objectIDs', [])
        if not ids:
            return []
        
        selected_ids = random.sample(ids[:20], min(limit, len(ids[:20])))
        results = []
        for obj_id in selected_ids:
            try:
                r_obj = requests.get(f"{MET_OBJECT_URL}{obj_id}", timeout=8)
                if r_obj.status_code == 200:
                    obj = r_obj.json()
                    title = obj.get('title') or 'Fotografía sin título'
                    artist = obj.get('artistDisplayName') or 'Autor anónimo'
                    date_str = obj.get('objectDate') or 'Sin fecha'
                    medium = obj.get('medium') or ''
                    img = obj.get('primaryImageSmall') or obj.get('primaryImage') or ''
                    
                    results.append({
                        'source': 'met_museum',
                        'institution': 'The Metropolitan Museum of Art, Nueva York',
                        'object_id': str(obj_id),
                        'title': title,
                        'photographer': artist,
                        'date': date_str,
                        'technique': medium,
                        'curatorial_notes': f"Fotografía de {artist} ({date_str}). Técnica: {medium}. Custodiada en el departamento de fotografía de The Met.",
                        'image_url': img,
                        'museum_url': obj.get('objectURL', '')
                    })
            except Exception:
                continue
        return results
    except Exception as e:
        logger.warning(f"Error consultando The Met API: {e}")
        return []


ES_TO_EN_PHOTO_TERMS = {
    'paisaje': 'landscape',
    'retrato': 'portrait',
    'calle': 'street',
    'urbano': 'urban',
    'arquitectura': 'architecture',
    'edificio': 'building',
    'naturaleza': 'nature',
    'mar': 'sea',
    'playa': 'beach',
    'oceano': 'ocean',
    'montana': 'mountain',
    'bosque': 'forest',
    'arbol': 'tree',
    'noche': 'night',
    'sombra': 'shadow',
    'sombras': 'shadows',
    'luz': 'light',
    'familia': 'family',
    'infancia': 'childhood',
    'nino': 'child',
    'ninos': 'children',
    'mujer': 'woman',
    'hombre': 'man',
    'gente': 'people',
    'viaje': 'travel',
    'camino': 'road',
    'carretera': 'highway',
    'ciudad': 'city',
    'trabajo': 'labor work',
    'cotidiano': 'everyday life',
    'memoria': 'memory',
    'soledad': 'solitude',
    'silencio': 'silence',
    'quimica': 'chemistry',
    'alquimia': 'alchemy',
    'estudio': 'studio',
    'forma': 'form',
    'color': 'color',
    'blanco': 'white',
    'negro': 'black',
}


def translate_to_en(query):
    """Convierte términos clave de fotografía del español al inglés para optimizar búsquedas en V&A y Met."""
    if not query:
        return 'landscape'
    q_norm = re.sub(r'[^\w\s]', '', query.lower())
    # Quitar tildes
    q_norm = q_norm.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    words = q_norm.split()
    translated = []
    for w in words:
        if w in ES_TO_EN_PHOTO_TERMS:
            translated.append(ES_TO_EN_PHOTO_TERMS[w])
        elif len(w) >= 4:
            translated.append(w)
    return ' '.join(translated) if translated else 'landscape'


def get_museum_treasure(keywords=None, prefer_source=None):
    """
    Selecciona de forma inteligente y rotativa una joya de museo para enriquecer el Linaje Visual:
    - Alterna entre el fondo de instituciones históricas (Tucson, Niépce, Gernsheim, MEP) y las APIs en vivo (V&A, Met).
    """
    choose_curated = prefer_source == 'curated' or (prefer_source is None and random.random() < 0.5)
    
    if choose_curated:
        curated_matches = search_curated_masters(keywords)
        if curated_matches:
            selected = random.choice(curated_matches[:3])
            return selected

    raw_query = "landscape"
    if keywords:
        if isinstance(keywords, list):
            raw_query = " ".join([str(k) for k in keywords[:3]])
        else:
            raw_query = str(keywords)

    query = translate_to_en(raw_query)

    candidates = []
    if random.random() < 0.5:
        candidates.extend(search_va_photographs(query, limit=2))
        if not candidates:
            candidates.extend(search_met_photographs(query, limit=2))
    else:
        candidates.extend(search_met_photographs(query, limit=2))
        if not candidates:
            candidates.extend(search_va_photographs(query, limit=2))

    if candidates:
        return random.choice(candidates)

    masters = load_curated_masters()
    return random.choice(masters) if masters else None


if __name__ == '__main__':
    print("Probando selector afinado...")
    for q in ['farm', 'street', 'quimica']:
        t = get_museum_treasure(q)
        if t:
            print(f"\n🏛️ [{t.get('institution')}]")
            print(f"📷 {t.get('title')} ({t.get('date')}) por {t.get('photographer')}")
            print(f"🔬 Técnica: {t.get('technique')}")
            print(f"📜 Notas: {t.get('curatorial_notes')[:200]}...")
