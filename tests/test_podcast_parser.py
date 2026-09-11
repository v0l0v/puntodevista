import os
import sys
import unittest
from pathlib import Path

# Añadir el directorio raíz al path para importar daily_podcast
DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DIR not in sys.path:
    sys.path.insert(0, DIR)

from daily_podcast import normalize_speaker_tags, validate_podcast_script


class TestPodcastSpeakerNormalization(unittest.TestCase):
    def test_normalize_hyphen_tags(self):
        """Verifica que etiquetas con triples guiones se canonicen a corchetes."""
        raw = (
            "[ROBERTO]\n"
            "Noticia de apertura.\n\n"
            "---BEATRIZ---\n"
            "Hola Roberto, aquí está mi análisis.\n\n"
            "---NICOLAS---\n"
            "Hola compañeros, aquí está el reto de hoy."
        )
        norm = normalize_speaker_tags(raw)
        self.assertIn("[BEATRIZ]", norm)
        self.assertIn("[NICOLAS]", norm)
        self.assertNotIn("---BEATRIZ---", norm)
        self.assertNotIn("---NICOLAS---", norm)

    def test_normalize_markdown_and_colons(self):
        """Verifica variantes con markdown, negrita y dos puntos."""
        cases = [
            ("**[BEATRIZ]**\nTexto de Beatriz", "[BEATRIZ]"),
            ("BEATRIZ:\nTexto de Beatriz", "[BEATRIZ]"),
            ("**NICOLÁS:**\nTexto de Nicolás", "[NICOLAS]"),
            ("[NICOLÁS]\nTexto de Nicolás", "[NICOLAS]"),
        ]
        for input_text, expected_tag in cases:
            norm = normalize_speaker_tags(input_text)
            self.assertIn(expected_tag, norm, f"Fallo al normalizar: {input_text}")

    def test_inline_speaker_names_preserved(self):
        """Verifica que menciones a locutores dentro de la prosa no se conviertan erróneamente en etiquetas."""
        raw = "Y para profundizar en este tema, os dejo con Beatriz. ¡Hola, Beatriz!"
        norm = normalize_speaker_tags(raw)
        self.assertEqual(norm, raw)
        self.assertNotIn("[BEATRIZ]", norm)


class TestPodcastQualityGate(unittest.TestCase):
    def test_valid_script_passes(self):
        """Un guion con turnos sustanciales de Roberto, Beatriz y Nicolás debe ser válido."""
        script = (
            "[ROBERTO]\n"
            "Bienvenidos a Punto de vista. Hoy tenemos un recorrido fascinante por la cultura visual internacional.\n\n"
            "[BEATRIZ]\n"
            "Hola Roberto y muy buenas a todos los oyentes. Hoy analizamos en profundidad la conexión entre archivo y luz.\n\n"
            "[NICOLAS]\n"
            "Gracias compañeros. Para el reto de hoy vamos a salir a la calle a buscar contrastes agresivos con óptica fija."
        )
        is_valid, errors, turns = validate_podcast_script(script)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertEqual(set(turns.keys()), {'ROBERTO', 'BEATRIZ', 'NICOLAS'})

    def test_missing_speaker_rejected(self):
        """Un guion al que le falte Beatriz o Nicolás debe ser rechazado con el error correspondiente."""
        script = (
            "[ROBERTO]\n"
            "Bienvenidos a Punto de vista. Hoy no ha podido venir nadie más.\n"
        )
        is_valid, errors, turns = validate_podcast_script(script)
        self.assertFalse(is_valid)
        self.assertTrue(any("Faltan intervenciones" in e for e in errors))
        self.assertTrue(any("BEATRIZ" in e for e in errors))
        self.assertTrue(any("NICOLAS" in e for e in errors))

    def test_script_with_hyphens_auto_recovers(self):
        """Un guion generado con ---BEATRIZ--- debe auto-repararse y superar el Quality Gate."""
        script = (
            "[ROBERTO]\n"
            "Bienvenidos a Punto de vista. Hoy tenemos un gran programa con noticias de todo el mundo.\n\n"
            "---BEATRIZ---\n"
            "Hola Roberto y muy buenas a todos. Qué maravilla de proyectos comentamos en la jornada de hoy.\n\n"
            "---NICOLAS---\n"
            "Gracias compañeros. Para el reto de hoy vamos a salir con una cámara de carrete y luz directa."
        )
        is_valid, errors, turns = validate_podcast_script(script)
        self.assertTrue(is_valid, f"Errores encontrados: {errors}")
        self.assertIn("BEATRIZ", turns)
        self.assertIn("NICOLAS", turns)


class TestHistoricalGuiones(unittest.TestCase):
    def test_all_historical_guiones_parseable(self):
        """Verifica que todos los archivos .guion.txt en resumenes/ se procesan sin errores."""
        resumenes_dir = Path(DIR) / 'resumenes'
        guion_files = list(resumenes_dir.glob('*.guion.txt'))
        self.assertGreater(len(guion_files), 0, "No se encontraron guiones en resumenes/")

        for gf in guion_files:
            content = gf.read_text(encoding='utf-8')
            norm = normalize_speaker_tags(content)
            self.assertIsInstance(norm, str)
            self.assertGreater(len(norm), 100, f"Guion {gf.name} sospechosamente vacío")


if __name__ == '__main__':
    unittest.main()
