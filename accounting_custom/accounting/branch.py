import frappe
from frappe import _
from frappe.utils import flt


def validate_accounting_payment_branch(doc, method=None):
	if not doc.custom_branch:
		frappe.throw(_("Branch is required."))
	branch_company = frappe.db.get_value("Branch", doc.custom_branch, "custom_company")
	if branch_company != doc.company:
		frappe.throw(_("Branch {0} does not belong to company {1}.").format(doc.custom_branch, doc.company))


def validate_journal_entry_branch(doc, method=None):
	for row in doc.accounts:
		if not row.custom_branch:
			continue
		branch_company = frappe.db.get_value("Branch", row.custom_branch, "custom_company")
		if branch_company != doc.company:
			frappe.throw(_("Row {0}: Branch {1} does not belong to company {2}.").format(
				row.idx, row.custom_branch, doc.company
			))


def set_gl_entry_branch(doc, method=None):
	set_journal_entry_transaction_currency(doc)

	if not frappe.get_meta("GL Entry").has_field("custom_branch"):
		return
	if doc.get("custom_branch") or not doc.voucher_type or not doc.voucher_no:
		return
	if doc.voucher_type == "Journal Entry" and doc.voucher_detail_no:
		doc.custom_branch = frappe.db.get_value("Journal Entry Account", doc.voucher_detail_no, "custom_branch")
	elif frappe.get_meta(doc.voucher_type).has_field("custom_branch"):
		doc.custom_branch = frappe.db.get_value(doc.voucher_type, doc.voucher_no, "custom_branch")


def set_journal_entry_transaction_currency(doc):
	"""Keep each Journal Entry row's original account currency in General Ledger."""
	if doc.get("voucher_type") != "Journal Entry" or not doc.get("account_currency"):
		return

	doc.transaction_currency = doc.account_currency
	doc.debit_in_transaction_currency = flt(doc.get("debit_in_account_currency"))
	doc.credit_in_transaction_currency = flt(doc.get("credit_in_account_currency"))

	account_amount = (
		doc.debit_in_transaction_currency
		if doc.debit_in_transaction_currency
		else doc.credit_in_transaction_currency
	)
	company_amount = flt(doc.get("debit")) if doc.debit_in_transaction_currency else flt(doc.get("credit"))
	if account_amount:
		doc.transaction_exchange_rate = company_amount / account_amount
