from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from accounting_custom.accounting.backfill_journals import _get_gl_rows


class TestJournalBackfill(TestCase):
	@patch("accounting_custom.accounting.backfill_journals.build_gl_entries", return_value=["donation-row"])
	def test_donation_uses_donation_builder(self, build):
		doc = SimpleNamespace(doctype="Donation Entry")
		self.assertEqual(_get_gl_rows(doc), ["donation-row"])
		build.assert_called_once_with(doc)

	def test_payment_and_receipt_use_controller_rows(self):
		for doctype in ("Accounting Payment Entry", "Accounting Receipt Entry"):
			doc = SimpleNamespace(doctype=doctype, get_gl_entries=lambda: [doctype])
			self.assertEqual(_get_gl_rows(doc), [doctype])
