from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.overrides.journal_entry import BaseJournalEntry, CustomJournalEntry


class TestCustomJournalEntry(FrappeTestCase):
	def test_payroll_rebuild_submits_large_journal_synchronously(self):
		journal = CustomJournalEntry({"doctype": "Journal Entry"})
		frappe.flags.accounting_custom_sync_journal_submit = True
		try:
			with patch.object(journal, "_submit", return_value="submitted") as synchronous_submit, patch.object(
				BaseJournalEntry, "submit"
			) as normal_submit:
				result = journal.submit()
		finally:
			frappe.flags.accounting_custom_sync_journal_submit = False

		self.assertEqual(result, "submitted")
		synchronous_submit.assert_called_once_with()
		normal_submit.assert_not_called()

	def _entry(self, **overrides):
		row = {
			"doctype": "Journal Entry Account",
			"idx": 1,
			"account": "PIA - CO",
			"party_type": "Employee",
			"party": "EMP-1",
			"reference_type": "Employee Advance",
			"reference_name": "ADV-1",
		}
		row.update(overrides)
		return CustomJournalEntry({"doctype": "Journal Entry", "accounts": [row]})

	def test_matching_employee_advance_allows_employee_on_receivable(self):
		entry = self._entry()
		with patch(
			"accounting_custom.overrides.journal_entry.frappe.get_cached_value",
			return_value="Receivable",
		), patch(
			"accounting_custom.overrides.journal_entry.frappe.db.get_value",
			side_effect=lambda doctype, _name, _fields, **_kwargs: (
				frappe._dict(employee="EMP-1", advance_account="PIA - CO")
				if doctype == "Employee Advance" else "Payable"
			),
		):
			entry.validate_party()

	def test_unrelated_receivable_mismatch_is_still_rejected(self):
		entry = self._entry(reference_type="Sales Invoice", reference_name="SINV-1")
		with patch(
			"accounting_custom.overrides.journal_entry.frappe.get_cached_value",
			return_value="Receivable",
		), patch(
			"accounting_custom.overrides.journal_entry.frappe.db.get_value",
			return_value="Payable",
		), self.assertRaises(frappe.ValidationError):
			entry.validate_party()

	def test_employee_advance_must_match_employee_and_account(self):
		entry = self._entry()
		with patch(
			"accounting_custom.overrides.journal_entry.frappe.get_cached_value",
			return_value="Receivable",
		), patch(
			"accounting_custom.overrides.journal_entry.frappe.db.get_value",
			side_effect=lambda doctype, _name, _fields, **_kwargs: (
				frappe._dict(employee="EMP-OTHER", advance_account="PIA - CO")
				if doctype == "Employee Advance" else "Payable"
			),
		), self.assertRaises(frappe.ValidationError):
			entry.validate_party()
