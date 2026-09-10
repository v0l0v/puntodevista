#!/usr/bin/env python3
"""
Módulo de Glosario Técnico Fotográfico para Punto de Vista.

Corrige sesgos, errores literales y artefactos del modelo neuronal de traducción
automática (CTranslate2 / Argos / OPUS-MT) hacia la terminología fotográfica precisa
y natural en español (castellano fotográfico y analógico).
"""

import re
from typing import List, Tuple, Pattern


def _match_case(source_text: str, replacement: str) -> str:
    """
    Preserva el estilo de mayúsculas/minúsculas del texto original:
    - TODO EN MAYÚSCULAS -> TODO EN MAYÚSCULAS
    - Capitalizado / Título -> Capitalizado
    - minúsculas -> minúsculas
    """
    if not source_text:
        return replacement
    if source_text.isupper() and len(source_text) > 1:
        return replacement.upper()
    if source_text[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement.lower()


def _make_rule(pattern_str: str, replacement: str) -> Tuple[Pattern, str]:
    """Compila una expresión regular con ignorar mayúsculas/minúsculas."""
    return re.compile(pattern_str, flags=re.IGNORECASE), replacement


# Reglas de sustitución organizadas por ámbito fotográfico
# Formato: (Regex con límites de palabra, término técnico correcto)
PHOTO_RULES: List[Tuple[Pattern, str]] = [
    # -------------------------------------------------------------
    # 1. CÁMARAS, VISORES Y FORMATOS
    # -------------------------------------------------------------
    _make_rule(r'\b(?:punto y filme cámara|punto y disparar cámara|punto y disparo cámara|cámara de punto y disparo|cámara de apunta y dispara|cámara apunta y dispara)\b', 'cámara compacta'),
    _make_rule(r'\b(?:punto y filme|punto y disparo)\b', 'apuntar y disparar'),
    _make_rule(r'\bformato mediano\b', 'formato medio'),
    _make_rule(r'\b(?:medio marco cámara|cámara de medio marco|medio marco)\b', 'medio cuadro (half-frame)'),
    _make_rule(r'\b(?:cámara de visor de rango|cámara de buscador de rango|cámara rangefinder)\b', 'cámara telemétrica'),
    _make_rule(r'\b(?:visor de rango|buscador de rango|rangefinder)\b', 'telémetro'),
    _make_rule(r'\b(?:visores de rango|buscadores de rango|rangefinders)\b', 'telémetros'),
    _make_rule(r'\b(?:cámara de agujeros|cámara estenopo)\b', 'cámara estenopeica'),
    _make_rule(r'\b(?:doble lente reflejo|cámara de doble lente reflejo|lente réflex doble|cámara TLR)\b', 'cámara réflex de dos objetivos (TLR)'),
    _make_rule(r'\b(?:cámara de visión de gran formato|cámara de vista de gran formato)\b', 'cámara técnica de gran formato'),
    _make_rule(r'\bcámara de visión\b', 'cámara técnica (banco óptico)'),
    _make_rule(r'\bcámara de película de 35 mm\b', 'cámara analógica de 35 mm'),
    _make_rule(r'\bcámara de película\b', 'cámara analógica'),
    _make_rule(r'\bcámaras de película\b', 'cámaras analógicas'),
    _make_rule(r'\bcámara de rollo\b', 'cámara de carrete'),
    _make_rule(r'\bcámaras de rollo\b', 'cámaras de carrete'),

    # -------------------------------------------------------------
    # 2. MECÁNICA, ÓPTICA Y ACCESORIOS
    # -------------------------------------------------------------
    _make_rule(r'\b(?:velocidad del transbordador|velocidad de transbordador)\b', 'velocidad de obturación'),
    _make_rule(r'\b(?:velocidad del obturador|velocidad de obturador)\b', 'velocidad de obturación'),
    _make_rule(r'\b(?:calzado caliente de la cámara|calzado caliente de cámara|calzado caliente|zapato caliente de la cámara|zapato caliente de cámara|zapato caliente)\b', 'zapata para flash'),
    _make_rule(r'\b(?:zapato frío de la cámara|zapato frío)\b', 'zapata fría'),
    _make_rule(r'\bde la cable disparador\b', 'del cable disparador'),
    _make_rule(r'\b(?:liberación de cable|liberación del cable)\b', 'cable disparador'),
    _make_rule(r'\blongitud focal\b', 'distancia focal'),
    _make_rule(r'\blongitudes focales\b', 'distancias focales'),
    _make_rule(r'\blente rápida\b', 'objetivo luminoso'),
    _make_rule(r'\blentes rápidas\b', 'objetivos luminosos'),
    _make_rule(r'\blente lenta\b', 'objetivo poco luminoso'),
    _make_rule(r'\blentes lentas\b', 'objetivos poco luminosos'),
    _make_rule(r'\bprofundidad poco profunda de campo\b', 'poca profundidad de campo'),
    _make_rule(r'\bprofundidad profunda de campo\b', 'gran profundidad de campo'),
    _make_rule(r'\b(?:círculo de confusión)\b', 'círculo de confusión'),
    _make_rule(r'\b(?:obturador foliar|obturador de hoja)\b', 'obturador central de láminas'),
    _make_rule(r'\b(?:medidor de luz portátil|medidor de luz de mano)\b', 'fotómetro de mano'),
    _make_rule(r'\bmedidor de luz\b', 'fotómetro'),
    _make_rule(r'\bmedidores de luz\b', 'fotómetros'),
    _make_rule(r'\bcuerpo de la cámara\b', 'cuerpo de la cámara'),
    _make_rule(r'\bcon bisel\b', 'con fuelle'),

    # -------------------------------------------------------------
    # 3. QUÍMICA, REVELADO Y CUARTO OSCURO
    # -------------------------------------------------------------
    _make_rule(r'\b(?:agrandador de cuarto oscuro|agrandador de la habitación oscura|agrandador y caballete de la habitación oscura)\b', 'ampliadora y marginador de laboratorio'),
    _make_rule(r'\b(?:agrandador fotográfico|agrandador de ampliación|agrandador|agrandar cuarto oscuro)\b', 'ampliadora'),
    _make_rule(r'\b(?:caballete de cuarto oscuro|caballete de la habitación oscura|caballete de ampliadora)\b', 'marginador'),
    _make_rule(r'\b(?:baño parar|parar el baño|parar baño|baño de parada|parada de baño)\b', 'baño de paro'),
    _make_rule(r'\b(?:tanque de desarrollo)\b', 'tanque de revelado'),
    _make_rule(r'\b(?:tanques de desarrollo)\b', 'tanques de revelado'),
    _make_rule(r'\b(?:recuperador del líder de cine|recuperador del líder de película|recuperador de líder|recuperador del líder)\b', 'extractor de lengüeta'),
    _make_rule(r'\b(?:líder de cine|líder de la película|líder de película)\b', 'lengüeta del carrete'),
    _make_rule(r'\bdesarrollador de película\b', 'revelador fotográfico'),
    _make_rule(r'\bdesarrollador fotográfico\b', 'revelador fotográfico'),
    _make_rule(r'\bdesarrollando película\b', 'revelando película'),
    _make_rule(r'\bdesarrollar película\b', 'revelar película'),
    _make_rule(r'\bdesarrollo de película\b', 'revelado de película'),
    _make_rule(r'\bdesarrollo de la película\b', 'revelado de la película'),
    _make_rule(r'\b(?:banda de prueba para impresión|banda de prueba)\b', 'tira de prueba'),
    _make_rule(r'\bhoja de contacto\b', 'hoja de contactos'),
    _make_rule(r'\bhojas de contacto\b', 'hojas de contactos'),
    _make_rule(r'\b(?:impresión de cuarto oscuro|impresión en cuarto oscuro)\b', 'positivado en cuarto oscuro'),
    _make_rule(r'\b(?:impresiones de cuarto oscuro|impresiones en cuarto oscuro)\b', 'positivados en cuarto oscuro'),
    _make_rule(r'\b(?:gelatina de plata|impresión con gelatina de plata|copia con gelatina de plata)\b', 'positivado a la plata en gelatina'),
    _make_rule(r'\b(?:impresión de cyanotipo|impresión de cianotipo)\b', 'copia al cianotipo'),
    _make_rule(r'\bhabitación oscura\b', 'cuarto oscuro'),
    _make_rule(r'\bplaca húmeda de colodión\b', 'colodión húmedo'),

    # -------------------------------------------------------------
    # 4. EMULSIONES, SENSIBILIDAD Y TÉCNICA
    # -------------------------------------------------------------
    _make_rule(r'\bblanco y negro fotografía\b', 'fotografía en blanco y negro'),
    _make_rule(r'\bpelícula blanca y negra\b', 'película en blanco y negro'),
    _make_rule(r'\bpelículas blancas y negras\b', 'películas en blanco y negro'),
    _make_rule(r'\bnegro y blanco\b', 'blanco y negro'),
    _make_rule(r'\bnegra y blanca\b', 'blanco y negro'),
    _make_rule(r'\bfotografía de cine blanco y negro\b', 'fotografía analógica en blanco y negro'),
    _make_rule(r'\bfotografía de cine\b', 'fotografía analógica'),
    _make_rule(r'\b(?:revisión del stock de película|reseña del stock de película|revisión de stock de película|reseña de stock de película)\b', 'reseña de película fotográfica'),
    _make_rule(r'\bstock de película\b', 'película fotográfica / emulsión'),
    _make_rule(r'\bacciones de película\b', 'emulsiones fotográficas'),
    _make_rule(r'\b(?:dos paradas de película de empuje|dos paradas de empuje)\b', 'forzar dos pasos'),
    _make_rule(r'\b(?:paradas de película de empuje|película de empuje)\b', 'forzado de película (push)'),
    _make_rule(r'\b(?:empujar película|empujando película)\b', 'forzar la película (push)'),
    _make_rule(r'\b(?:tirar película|tirando película)\b', 'subdesarrollar la película (pull)'),
    _make_rule(r'\bparadas de luz\b', 'pasos de luz'),
    _make_rule(r'\bparadas de exposición\b', 'pasos de exposición'),
    _make_rule(r'\b(?:parada f|f-parada)\b', 'paso f'),
    _make_rule(r'\b(?:paradas f|f-paradas)\b', 'pasos f'),
    _make_rule(r'\bprioridad de apertura\b', 'prioridad a la apertura'),
    _make_rule(r'\bprioridad de obturación\b', 'prioridad a la obturación'),
    _make_rule(r'\b(?:desenmascarados y sombras aplastadas|altas luces sopladas y sombras aplastadas)\b', 'altas luces quemadas y sombras empastadas'),
    _make_rule(r'\b(?:luces altas sopladas|altas luces sopladas)\b', 'altas luces quemadas'),
    _make_rule(r'\b(?:sombras aplastadas|sombras aplastadas)\b', 'sombras empastadas'),
    _make_rule(r'\bestructura de la hilera y agudeza\b', 'estructura de grano y nitidez'),
    _make_rule(r'\bestructura de la hilera\b', 'estructura del grano'),
    _make_rule(r'\bhilera y agudeza\b', 'grano y nitidez'),
    _make_rule(r'\bhaluro de plata\b', 'halogenuro de plata'),
    _make_rule(r'\bhaluros de plata\b', 'halogenuros de plata'),
    _make_rule(r'\bpelícula de diapositivas\b', 'película diapositiva'),
    _make_rule(r'\brollo de película\b', 'carrete'),
    _make_rule(r'\brollos de película\b', 'carretes'),

    # -------------------------------------------------------------
    # 5. EDITORIAL Y GÉNEROS
    # -------------------------------------------------------------
    _make_rule(r'\b(?:photobook review|revisión de fotolibro)\b', 'reseña de fotolibro'),
    _make_rule(r'\bfotobook revisión\b', 'reseña de fotolibro'),
    _make_rule(r'\bfotobook\b', 'fotolibro'),
    _make_rule(r'\bfotobooks\b', 'fotolibros'),
    _make_rule(r'\blibro de fotos\b', 'fotolibro'),
    _make_rule(r'\blibros de fotos\b', 'fotolibros'),
    _make_rule(r'\bhardcover\b', 'tapa dura'),
    _make_rule(r'\bsoftcover\b', 'tapa blanda'),
    _make_rule(r'\bcalle fotografía\b', 'fotografía de calle'),
]


def apply_photo_glossary(text: str) -> str:
    """
    Aplica las reglas del glosario técnico fotográfico a una cadena de texto en español.
    Preserva el estilo de mayúsculas (capitalización de inicio de frase o mayúsculas completas).
    """
    if not text or not isinstance(text, str):
        return text

    processed = text
    for pattern, replacement in PHOTO_RULES:
        def repl(m: re.Match) -> str:
            return _match_case(m.group(0), replacement)

        processed = pattern.sub(repl, processed)

    return processed


if __name__ == '__main__':
    # Batería de pruebas de verificación
    test_cases = [
        ("Fotografía de cine blanco y negro con cámara de película de 35 mm y rangefinder.",
         "Fotografía analógica en blanco y negro con cámara analógica de 35 mm y telémetro."),
        ("Punto y filme cámara para fotografía callejera.",
         "Cámara compacta para fotografía callejera."),
        ("Agrandador y caballete de la habitación oscura con parada de baño.",
         "Ampliadora y marginador de laboratorio con baño de paro."),
        ("Velocidad del transbordador y zapato caliente de la cámara con liberación de cable.",
         "Velocidad de obturación y zapata para flash con cable disparador."),
        ("Desarrollando película blanca y negra con tanque de desarrollo y recuperador del líder de cine.",
         "Revelando película blanca y negra con tanque de revelado y extractor de lengüeta."),
        ("Desenmascarados y sombras aplastadas con estructura de la hilera y agudeza.",
         "Altas luces quemadas y sombras empastadas con estructura de grano y nitidez."),
        ("Fotobook revisión de formato mediano con haluros de plata.",
         "Reseña de fotolibro de formato medio con halogenuros de plata.")
    ]

    print("🧪 Ejecutando pruebas del glosario fotográfico...")
    all_passed = True
    for original, expected in test_cases:
        result = apply_photo_glossary(original)
        passed = (result == expected)
        if not passed:
            all_passed = False
            print(f"❌ FALLO:\n  Original: {original}\n  Esperado: {expected}\n  Obtenido: {result}")
        else:
            print(f"✅ OK: {result}")

    if all_passed:
        print("\n✨ ¡Todas las pruebas del glosario pasaron exitosamente!")
