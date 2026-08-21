import json
import os

DIR = os.path.dirname(os.path.abspath(__file__))
SOURCES_FILE = os.path.join(DIR, 'sources.json')

def load_sources_config():
    """Carga la lista completa de fuentes configuradas en sources.json."""
    if os.path.exists(SOURCES_FILE):
        try:
            with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error cargando {SOURCES_FILE}: {e}")
    return []

def get_active_sources():
    """Devuelve solo las fuentes con enabled: True."""
    return [s for s in load_sources_config() if s.get('enabled', True)]

def get_source_by_id(source_id):
    """Busca una fuente específica por su identificador."""
    for s in load_sources_config():
        if s.get('id') == source_id:
            return s
    return None

def get_source_label(source_id, default=None):
    """Obtiene el nombre público/editorial de una fuente."""
    s = get_source_by_id(source_id)
    if s and s.get('name'):
        return s['name']
    return default or source_id
