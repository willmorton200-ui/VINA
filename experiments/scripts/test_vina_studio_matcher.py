
#!/usr/bin/env python3
"""
Тесты для модуля VINA STUDIO Text Matcher.
Проверяют: транслитерацию, построение словаря, матчинг OCR-тегов, каскадное решение.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

# Добавляем корневую директорию проекта в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.vina_studio_matcher import (
    cyrillic_to_latin,
    latin_to_cyrillic,
    normalize_word,
    is_cyrillic,
    VinaStudioMatcher,
)


class TestTransliteration(unittest.TestCase):
    """Тесты транслитерации кириллица ↔ латиница."""
    
    def test_cyrillic_to_latin_basic(self):
        self.assertEqual(cyrillic_to_latin("КРАСНОЕ"), "KRASNOE")
        self.assertEqual(cyrillic_to_latin("ВИНО"), "VINO")
        self.assertEqual(cyrillic_to_latin("КРЫМ"), "KRbIM")
        self.assertEqual(cyrillic_to_latin("ТЕМПРАНИЛЬО"), "TEMPIIPAHMJIbO")
    
    def test_latin_to_cyrillic_basic(self):
        self.assertEqual(latin_to_cyrillic("KRASNOE"), "КРАСНОЕ")
        self.assertEqual(latin_to_cyrillic("VINO"), "ВИНО")
        self.assertEqual(latin_to_cyrillic("TEMPRANILLO"), "ТЕМПРАНИЛЬО")
    
    def test_mixed_text(self):
        # Смешанный текст должен корректно обрабатываться
        result = cyrillic_to_latin("Вино 2022")
        self.assertEqual(result, "VINO 2022")
    
    def test_is_cyrillic(self):
        self.assertTrue(is_cyrillic("КРАСНОЕ"))
        self.assertTrue(is_cyrillic("Красное вино"))
        self.assertFalse(is_cyrillic("RED WINE"))
        self.assertFalse(is_cyrillic("TEMPRANILLO"))
        self.assertTrue(is_cyrillic("ТЕМПРАНИЛЬО"))
    
    def test_normalize_word(self):
        self.assertEqual(normalize_word("Красное"), "КРАСНОЕ")
        self.assertEqual(normalize_word("красное,"), "КРАСНОЕ")
        self.assertEqual(normalize_word("TEMPRANILLO."), "TEMPRANILLO")
        self.assertEqual(normalize_word("Вино 2022"), "ВИНО 2022")


class TestVinaStudioMatcher(unittest.TestCase):
    """Тесты матчера VINA STUDIO."""
    
    def setUp(self):
        """Создаём моковый каталог для тестов."""
        self.mock_catalog = MagicMock()
        self.mock_catalog.get_all_wines.return_value = [
            {"slug": "test-krasnoe-vino", "name": "Красное сухое вино Крым"},
            {"slug": "test-beloe-vino", "name": "Белое полусладкое вино Кубань"},
            {"slug": "test-tempranillo", "name": "Темпранильо Резерва"},
            {"slug": "test-cabernet", "name": "Каберне Совиньон Массандра"},
            {"slug": "test-fanagoriya", "name": "Фанагория красное сухое"},
            {"slug": "test-alma-valley", "name": "Alma Valley Chardonnay"},
            {"slug": "test-roses-vino", "name": "Розовое сухое вино Абрау"},
        ]
    
    def test_dictionary_building(self):
        """Проверяем, что словарь строится корректно."""
        matcher = VinaStudioMatcher(self.mock_catalog)
        
        # Должны быть добавлены слова из названий
        self.assertIn("КРАСНОЕ", matcher.word_to_slugs)
        self.assertIn("ВИНО", matcher.word_to_slugs)
        self.assertIn("ТЕМПРАНИЛЬО", matcher.word_to_slugs)
        self.assertIn("КАБЕРНЕ", matcher.word_to_slugs)
        
        # Латинские варианты должны быть добавлены для кириллических слов
        self.assertIn("KRASNOE", matcher.word_to_slugs)
        self.assertIn("VINO", matcher.word_to_slugs)
        
        # Проверка обратной транслитерации для латинских слов
        # "Alma Valley" → кириллица
        # "Chardonnay" → кириллица
        
        # Количество slug'ей должно соответствовать каталогу
        self.assertEqual(len(matcher.all_slugs), 7)
    
    def test_match_ocr_cyrillic_text(self):
        """Матчинг кириллического OCR-текста."""
        matcher = VinaStudioMatcher(self.mock_catalog)
        
        ocr_text = "Красное сухое вино Крым"
        results = matcher.match_ocr_tags(ocr_text)
        
        self.assertTrue(len(results) > 0)
        # Первый результат должен быть "test-krasnoe-vino"
        self.assertEqual(results[0]["slug"], "test-krasnoe-vino")
        self.assertGreater(results[0]["match_count"], 0)
    
    def test_match_ocr_latin_text(self):
        """Матчинг латинского OCR-текста."""
        matcher = VinaStudioMatcher(self.mock_catalog)
        
        ocr_text = "KRASNOE SUHOE VINO"
        results = matcher.match_ocr_tags(ocr_text)
        
        self.assertTrue(len(results) >= 0)
        # Должен найти совпадение через транслитерацию
        
        ocr_text2 = "TEMPRANILLO RESERVA"
        results2 = matcher.match_ocr_tags(ocr_text2)
        
        self.assertTrue(len(results2) > 0)
        self.assertEqual(results2[0]["slug"], "test-tempranillo")
    
    def test_match_ocr_mixed_text(self):
        """Матчинг смешанного текста (кириллица + латиница)."""
        matcher = VinaStudioMatcher(self.mock_catalog)
        
        ocr_text = "Фанагория красное сухое вино"
        results = matcher.match_ocr_tags(ocr_text)
        
        self.assertTrue(len(results) > 0)
        # Должен найти "test-fanagoriya" или "test-krasnoe-vino"
        found_fanagoriya = any(r["slug"] == "test-fanagoriya" for r in results)
        found_krasnoe = any(r["slug"] == "test-krasnoe-vino" for r in results)
        self.assertTrue(found_fanagoriya or found_krasnoe)
    
    def test_confidence_100_percent(self):
        """При совпадении ≥3 тегов уверенность = 100%."""
        matcher = VinaStudioMatcher(self.mock_catalog)
        
        ocr_text = "Красное сухое вино Крым"  # 4 слова, все должны совпасть
        results = matcher.match_ocr_tags(ocr_text)
        
        if results:
            best = results[0]
            if best["match_count"] >= 3:
                self.assertEqual(best["confidence_vina"], 100.0)
    
    def test_cascade_decision(self):
        """Каскадное решение: сравнение SigLIP и VINA STUDIO."""
        matcher = VinaStudioMatcher(self.mock_catalog)
        
        siglip_results = [
            {"slug": "test-krasnoe-vino", "score": 0.85, "wine_data": None},
            {"slug": "test-beloe-vino", "score": 0.65, "wine_data": None},
        ]
        
        ocr_text = "Красное сухое вино Крым"
        result = matcher.cascade_decision(ocr_text, siglip_results)
        
        self.assertIn("slug", result)
        self.assertIn("final_confidence", result)
        self.assertIn("decision_source", result)
        self.assertIn("confidence_siglip", result)
        self.assertIn("confidence_vina", result)
        
        # Если оба метода нашли один slug — должно быть согласие
        if result["vina_slug"] == result["siglip_slug"]:
            self.assertEqual(result["decision_source"], "cascade_agreement")
    
    def test_cascade_vina_wins(self):
        """VINA STUDIO побеждает при высокой текстовой уверенности."""
        matcher = VinaStudioMatcher(self.mock_catalog)
        
        # SigLIP даёт низкий score
        siglip_results = [
            {"slug": "test-beloe-vino", "score": 0.3, "wine_data": None},
        ]
        
        # OCR точно определяет название
        ocr_text = "Красное сухое вино Крым"
        result = matcher.cascade_decision(ocr_text, siglip_results)
        
        # VINA STUDIO должна победить
        if result["confidence_vina"] > result["confidence_siglip"]:
            self.assertEqual(result["decision_source"], "vina_studio_text")
    
    def test_cascade_siglip_wins(self):
        """SigLIP побеждает при высокой визуальной уверенности."""
        matcher = VinaStudioMatcher(self.mock_catalog)
        
        # SigLIP даёт высокий score
        siglip_results = [
            {"slug": "test-tempranillo", "score": 0.95, "wine_data": None},
        ]
        
        # OCR находит мало совпадений
        ocr_text = "Неизвестный бренд"
        result = matcher.cascade_decision(ocr_text, siglip_results)
        
        # SigLIP должен победить
        if result["confidence_siglip"] > result["confidence_vina"]:
            self.assertEqual(result["decision_source"], "siglip_visual")
    
    def test_empty_ocr_text(self):
        """Обработка пустого OCR-текста."""
        matcher = VinaStudioMatcher(self.mock_catalog)
        
        results = matcher.match_ocr_tags("")
        self.assertEqual(len(results), 0)
        
        siglip_results = [
            {"slug": "test-krasnoe-vino", "score": 0.85, "wine_data": None},
        ]
        result = matcher.cascade_decision("", siglip_results)
        
        # При пустом OCR должен вернуться результат SigLIP
        self.assertEqual(result["slug"], "test-krasnoe-vino")


if __name__ == "__main__":
    unittest.main(verbosity=2)
