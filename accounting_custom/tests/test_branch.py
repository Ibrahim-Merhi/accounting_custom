from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from accounting_custom.accounting.branch import validate_journal_entry_branch


class TestBranchValidation(TestCase):
	def setUp(self):
		translation = patch("accounting_custom.accounting.branch._", side_effect=lambda message: message)
		translation.start()
		self.addCleanup(translation.stop)

	@patch("accounting_custom.accounting.branch.frappe.db.get_value", return_value="Itihad")
	def test_matching_branch_company_is_allowed(self, _get_value):
		validate_journal_entry_branch(SimpleNamespace(company="Itihad", accounts=[SimpleNamespace(idx=1, custom_branch="Beirut")]))

	@patch("accounting_custom.accounting.branch.frappe.throw", side_effect=frappe.ValidationError)
	@patch("accounting_custom.accounting.branch.frappe.db.get_value", return_value="Other")
	def test_cross_company_branch_is_rejected(self, _get_value, _throw):
		with self.assertRaises(frappe.ValidationError):
			validate_journal_entry_branch(SimpleNamespace(company="Itihad", accounts=[SimpleNamespace(idx=1, custom_branch="Beirut")]))
