from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from accounting_custom.accounting.backfill_journals import (
	_get_gl_rows,
	_normalize_legacy_parties,
)


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

	@patch("accounting_custom.accounting.backfill_journals.frappe")
	def test_receivable_mismatch_maps_to_custody_by_account(self, frappe_mock):
		get_value = Mock()
		get_value.side_effect = ["Receivable", "Payable", "Sheikh Hassan Katerji"]
		frappe_mock.db.get_value = get_value
		doc = SimpleNamespace(company="Itihad")
		row = frappe._dict(
			account="46990001 - Sheikh Hassan Katerji - ITHD",
			party_type="Institution",
			party="Institution 1",
		)

		_normalize_legacy_parties(doc, [row])

		self.assertEqual(row.party_type, "Custodies")
		self.assertEqual(row.party, "Sheikh Hassan Katerji")
