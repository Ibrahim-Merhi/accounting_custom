from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from accounting_custom.accounting.journal_posting import (
	cancel_linked_journal_entry,
	create_linked_journal_entry,
)


class TestLinkedJournalPosting(TestCase):
	@patch("accounting_custom.accounting.journal_posting.frappe.get_doc")
	def test_create_submits_and_links_journal(self, get_doc):
		journal = MagicMock()
		journal.name = "JV-0001"
		get_doc.return_value = journal
		source = MagicMock(
			journal_entry=None, company="Itihad", posting_date="2026-09-05",
			remarks="Receipt", doctype="Accounting Receipt Entry", name="ARE-0001",
		)
		row = frappe._dict(
			account="Cash USD", account_currency="USD", debit=100, credit=0,
			debit_in_account_currency=100, credit_in_account_currency=0,
			cost_center="Main - ITHD", remarks="Receipt",
		)

		name = create_linked_journal_entry(source, [row])

		self.assertEqual(name, "JV-0001")
		journal.insert.assert_called_once_with()
		journal.submit.assert_called_once_with()
		source.db_set.assert_called_once_with("journal_entry", "JV-0001", update_modified=False)
		self.assertTrue(journal.flags.ignore_company_exchange_rate)

	@patch("accounting_custom.accounting.journal_posting.frappe.get_doc")
	def test_cancel_cancels_linked_submitted_journal(self, get_doc):
		journal = MagicMock(docstatus=1)
		get_doc.return_value = journal
		source = SimpleNamespace(
			doctype="Donation Entry", journal_entry="JV-0001",
		)

		cancel_linked_journal_entry(source)

		journal.cancel.assert_called_once_with()
		self.assertEqual(journal.ignore_linked_doctypes, ("Donation Entry",))
