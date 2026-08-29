from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from accounting_custom.accounting_custom.doctype.payment_memo.payment_memo import PaymentMemo
from accounting_custom.accounting_custom.doctype.payment_memo.payment_memo import transition


class TestPaymentMemoGL(TestCase):
	@patch("accounting_custom.accounting_custom.doctype.payment_memo.payment_memo.frappe.get_cached_value")
	@patch("accounting_custom.accounting_custom.doctype.payment_memo.payment_memo.get_account_details")
	def test_builds_balanced_rows_for_multiple_cost_centers(self, account_details, company_currency):
		company_currency.return_value = "USD"
		account_details.return_value = frappe._dict(account_currency="USD")
		doc = SimpleNamespace(
			company="Namaa", posting_date="2026-08-28", currency="USD",
			payment_account="Cash - NAM", doctype="Payment Memo", name="PM-1",
			project=None, payment_type="Payment", exchange_rate=1,
			allocations=[
				SimpleNamespace(idx=1, account="Expense A", cost_center="CC-A", project=None, amount=60, description="A"),
				SimpleNamespace(idx=2, account="Expense B", cost_center="CC-B", project="P-1", amount=40, description="B"),
			],
		)

		rows = PaymentMemo.get_gl_entries(doc)

		self.assertEqual(len(rows), 4)
		self.assertEqual(sum(row.debit for row in rows), 100)
		self.assertEqual(sum(row.credit for row in rows), 100)
		self.assertEqual({row.cost_center for row in rows}, {"CC-A", "CC-B"})
		self.assertEqual(rows[2].project, "P-1")


class TestPaymentMemoApproval(TestCase):
	@patch("accounting_custom.accounting_custom.doctype.payment_memo.payment_memo.frappe.throw", side_effect=frappe.ValidationError)
	@patch("accounting_custom.accounting_custom.doctype.payment_memo.payment_memo._", side_effect=lambda message: message)
	@patch("accounting_custom.accounting_custom.doctype.payment_memo.payment_memo.frappe.session", SimpleNamespace(user="manager-b@example.com"))
	@patch("accounting_custom.accounting_custom.doctype.payment_memo.payment_memo.frappe.get_roles", return_value=["Responsible Manager"])
	@patch("accounting_custom.accounting_custom.doctype.payment_memo.payment_memo.frappe.get_doc")
	def test_only_selected_manager_can_approve(self, get_doc, _get_roles, _translate, _throw):
		get_doc.return_value = SimpleNamespace(
			docstatus=0, approval_status="Pending Manager",
			responsible_manager="manager-a@example.com",
		)

		with self.assertRaises(frappe.ValidationError):
			transition("PM-1", "Approve")
