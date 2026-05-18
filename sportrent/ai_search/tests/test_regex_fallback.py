"""
Unit-тесты для RegexFallbackProvider.

Все тесты используют только RegexFallbackProvider напрямую —
GigaChat API не вызывается, токены не расходуются.
"""

from datetime import date, timedelta
from django.test import SimpleTestCase

from ai_search.services.llm import RegexFallbackProvider


class RegexFallbackProviderTest(SimpleTestCase):
    """15+ тестов парсера без обращений к внешним API."""

    def setUp(self):
        self.p = RegexFallbackProvider()

    # ── Города: разные падежи и синонимы ──────────────────────────────────

    def test_city_nominative_moscow(self):
        """Именительный падеж — «Москва»."""
        r = self.p.parse_query('лыжи Москва недорого')
        self.assertEqual(r.city_name, 'Москва')

    def test_city_prepositional_moscow(self):
        """Предложный падеж — «в Москве»."""
        r = self.p.parse_query('велосипед в Москве до 500')
        self.assertEqual(r.city_name, 'Москва')

    def test_city_synonym_piter(self):
        """Синоним «питер» → Санкт-Петербург."""
        r = self.p.parse_query('роликовые коньки в питере')
        self.assertEqual(r.city_name, 'Санкт-Петербург')

    def test_city_abbreviation_spb(self):
        """Аббревиатура «спб» → Санкт-Петербург."""
        r = self.p.parse_query('велосипед спб')
        self.assertEqual(r.city_name, 'Санкт-Петербург')

    def test_city_genitive_kazan(self):
        """Родительный падеж — «в Казани»."""
        r = self.p.parse_query('аренда самоката в казани')
        self.assertEqual(r.city_name, 'Казань')

    def test_city_abbreviation_ekb(self):
        """Аббревиатура «екб» → Екатеринбург."""
        r = self.p.parse_query('сноуборд в екб на выходных')
        self.assertEqual(r.city_name, 'Екатеринбург')

    def test_city_ufa_dative(self):
        """Дательный падеж — «в Уфе»."""
        r = self.p.parse_query('коньки в уфе')
        self.assertEqual(r.city_name, 'Уфа')

    # ── Категории: единственное и множественное число ─────────────────────

    def test_category_ski_specific(self):
        """Беговые лыжи — более специфичная категория."""
        r = self.p.parse_query('беговые лыжи в Казани до 800')
        self.assertEqual(r.category_query, 'беговые лыжи')

    def test_category_ski_plural(self):
        """«Лыжи» без уточнения → общая категория."""
        r = self.p.parse_query('лыжи в Новосибирске')
        self.assertIn(r.category_query, ('беговые лыжи', 'горные лыжи', 'лыжи'))

    def test_category_bicycle_plural(self):
        """Множественное число — «велосипеды»."""
        r = self.p.parse_query('велосипеды на выходных в Москве')
        self.assertEqual(r.category_query, 'велосипед')

    def test_category_snowboard(self):
        """«Сноуборд» в запросе."""
        r = self.p.parse_query('сноуборд в Сочи недорого')
        self.assertEqual(r.category_query, 'сноуборд')

    # ── Цены: разные форматы ──────────────────────────────────────────────

    def test_price_do(self):
        """«до 1000» → 1000.0."""
        r = self.p.parse_query('лыжи до 1000 рублей')
        self.assertEqual(r.max_price, 1000.0)

    def test_price_ne_dorozhe(self):
        """«не дороже 500»."""
        r = self.p.parse_query('велосипед не дороже 500 в Уфе')
        self.assertEqual(r.max_price, 500.0)

    def test_price_k_suffix(self):
        """«до 1.5к» → 1500.0."""
        r = self.p.parse_query('коньки до 1.5к в день')
        self.assertEqual(r.max_price, 1500.0)

    # ── Даты ─────────────────────────────────────────────────────────────

    def test_date_tomorrow(self):
        """«завтра» → следующий день."""
        r = self.p.parse_query('велосипед завтра')
        expected = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(r.start_date, expected)

    def test_date_weekend_start_and_end(self):
        """«на выходных» → start_date и end_date не None."""
        r = self.p.parse_query('лыжи на выходных в Казани')
        self.assertIsNotNone(r.start_date)
        self.assertIsNotNone(r.end_date)

    def test_date_explicit_june(self):
        """«15 июня» → start_date содержит -06-15."""
        r = self.p.parse_query('лыжи 15 июня')
        self.assertIsNotNone(r.start_date)
        self.assertIn('-06-15', r.start_date)

    # ── Крайние случаи ───────────────────────────────────────────────────

    def test_no_city_returns_none(self):
        """Запрос без города → city_name is None."""
        r = self.p.parse_query('беговые лыжи до 800 рублей')
        self.assertIsNone(r.city_name)
        self.assertEqual(r.category_query, 'беговые лыжи')

    def test_city_only_no_category(self):
        """Только город → category_query is None."""
        r = self.p.parse_query('казань')
        self.assertEqual(r.city_name, 'Казань')
        self.assertIsNone(r.category_query)

    def test_no_category_returns_none(self):
        """Запрос без категории → category_query is None."""
        r = self.p.parse_query('аренда в москве до 500')
        self.assertEqual(r.city_name, 'Москва')
        self.assertIsNone(r.category_query)

    def test_empty_query_returns_empty(self):
        """Пустая строка → все поля None."""
        r = self.p.parse_query('')
        self.assertIsNone(r.city_name)
        self.assertIsNone(r.category_query)
        self.assertIsNone(r.max_price)
