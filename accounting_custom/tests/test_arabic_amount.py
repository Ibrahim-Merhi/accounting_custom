from unittest import TestCase

from accounting_custom.utils.arabic_amount import arabic_amount_in_words


class TestArabicAmount(TestCase):
	def test_approved_examples(self):
		examples = {
			(200, "USD"): "مائتي دولار أمريكي فقط لا غير",
			(200, "LBP"): "مائتي ليرة لبنانية فقط لا غير",
			(1200, "USD"): "ألف ومائتي دولار أمريكي فقط لا غير",
			(200000, "LBP"): "مائتي ألف ليرة لبنانية فقط لا غير",
			(5775000, "LBP"): "خمسة ملايين وسبعمائة وخمسة وسبعون ألف ليرة لبنانية فقط لا غير",
		}
		for arguments, expected in examples.items():
			with self.subTest(arguments=arguments):
				self.assertEqual(arabic_amount_in_words(*arguments), expected)

	def test_usd_cents(self):
		self.assertEqual(
			arabic_amount_in_words(500.25, "USD"),
			"خمسمائة دولار أمريكي وخمسة وعشرون سنتًا أمريكيًا فقط لا غير",
		)

	def test_representative_values(self):
		for value in (0, 1, 2, 3, 10, 11, 12, 20, 25, 100, 500, 1000, 2000, 89500000):
			with self.subTest(value=value):
				self.assertTrue(arabic_amount_in_words(value, "USD").endswith("فقط لا غير"))
				self.assertTrue(arabic_amount_in_words(value, "LBP").endswith("فقط لا غير"))
