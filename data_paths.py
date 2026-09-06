#!/usr/bin/env python3
"""
data_paths.py — Single Source of Truth (SSOT) para rutas de datos y cachés.
Garantiza el aislamiento de datos en data/ con fallback transparente a raíz.
"""
import os

DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)


def get_data_path(filename: str) -> str:
    """Devuelve la ruta canónica en data/, o la raíz si el archivo aún reside allí."""
    data_path = os.path.join(DATA_DIR, filename)
    root_path = os.path.join(DIR, filename)
    if os.path.exists(data_path):
        return data_path
    if os.path.exists(root_path):
        return root_path
    return data_path


def get_data_dir() -> str:
    """Devuelve la ruta absoluta al directorio data/."""
    return DATA_DIR


def get_db_path() -> str:
    """Devuelve la ruta canónica a archive.db (priorizando data/ y fallback a raíz)."""
    return get_data_path('archive.db')
