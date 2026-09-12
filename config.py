#!/usr/bin/env python3
"""
Módulo centralizado de configuración (Single Source of Truth) para Punto de Vista.
Gestiona la lectura de config.json, variables de entorno, credenciales y detección del proxy WARP.
"""
import os
import json
import socket
import logging

logger = logging.getLogger('pdv.config')

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(DIR, 'config.json')

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(DIR, '.env'))
except ImportError:
    pass

_CONFIG = {}

def load_config():
    """Carga config.json de manera tolerante a fallos."""
    global _CONFIG
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                _CONFIG = json.load(f)
        except Exception as e:
            logger.warning(f"No se pudo leer {CONFIG_PATH}: {e}")
            _CONFIG = {}
    return _CONFIG

# Inicialización al importar el módulo
load_config()

# Compatibilidad con código existente que acceda a CONFIG como dict
CONFIG = _CONFIG

def get_config(key, default=None):
    """
    Obtiene un valor de configuración con prioridad:
    1. Variable de entorno (.env o sistema)
    2. config.json
    3. Valor por defecto
    """
    val = os.environ.get(key)
    if val is not None and val != '':
        return val
    return _CONFIG.get(key, default)

def get_openai_base_url(default='http://127.0.0.1:8090/v1'):
    """Retorna la URL base del proveedor LLM compatible con OpenAI."""
    return get_config('OPENAI_BASE_URL', default)

def get_openai_api_key(default='local-no-key'):
    """Retorna la API key para el proveedor LLM."""
    return get_config('OPENAI_API_KEY', default)

def get_llm_model(default='qwen2.5-7b-instruct'):
    """Retorna el nombre del modelo LLM configurado."""
    return get_config('MODEL_NAME') or get_config('LLM_MODEL', default)

def get_llm_config():
    """Retorna tupla (base_url, api_key, model_name)."""
    return get_openai_base_url(), get_openai_api_key(), get_llm_model()

def get_gemini_key():
    """Retorna la clave de API de Gemini (legacy)."""
    return get_config('GEMINI_KEY') or get_config('GEMINI_API_KEY')

def get_gemini_model(default='gemini-flash-latest'):
    """Retorna el modelo preferido de Gemini (legacy)."""
    return get_config('GEMINI_MODEL', default)

def get_telegram_creds():
    """
    Retorna tupla (bot_token, chat_id) para Telegram.
    Soporta alias TG_TOKEN / TELEGRAM_BOT_TOKEN y TG_CHAT_ID / TELEGRAM_CHAT_ID.
    """
    token = get_config('TG_TOKEN') or get_config('TELEGRAM_BOT_TOKEN') or get_config('TELEGRAM_TOKEN')
    chat_id = get_config('TG_CHAT_ID') or get_config('TELEGRAM_CHAT_ID') or get_config('TELEGRAM_CHANNEL_ID')
    return token, chat_id

def get_jina_key():
    """Retorna la clave de API de Jina."""
    return get_config('JINA_API_KEY')

def get_email_config():
    """Retorna el diccionario de configuración de correo."""
    raw = _CONFIG.get('email', {})
    address = os.environ.get('EMAIL_ADDRESS') or raw.get('address')
    app_password = os.environ.get('EMAIL_APP_PASSWORD') or raw.get('app_password')
    imap_server = os.environ.get('EMAIL_IMAP_SERVER') or raw.get('imap_server', 'imap.gmail.com')
    return {
        'address': address,
        'app_password': app_password,
        'imap_server': imap_server
    }

def ensure_warp_proxy(port=40000, host='127.0.0.1'):
    """
    Verifica si Cloudflare WARP SOCKS5 está activo en el puerto indicado.
    Si está activo y HTTPS_PROXY no está configurado, lo exporta a os.environ.
    Retorna True si el proxy está activo.
    """
    proxy_url = f"socks5h://{host}:{port}"
    if os.environ.get('HTTPS_PROXY') == proxy_url:
        return True

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex((host, port)) == 0:
                os.environ['HTTPS_PROXY'] = proxy_url
                os.environ['HTTP_PROXY'] = proxy_url
                return True
    except Exception:
        pass
    return False

# Autodetección inmediata de WARP
ensure_warp_proxy()
