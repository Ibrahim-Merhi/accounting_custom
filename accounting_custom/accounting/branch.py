import frappe
from frappe import _


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
	if not frappe.get_meta("GL Entry").has_field("custom_branch"):
		return
	if doc.get("custom_branch") or not doc.voucher_type or not doc.voucher_no:
		return
	if doc.voucher_type == "Journal Entry" and doc.voucher_detail_no:
		doc.custom_branch = frappe.db.get_value("Journal Entry Account", doc.voucher_detail_no, "custom_branch")
	elif frappe.get_meta(doc.voucher_type).has_field("custom_branch"):
		doc.custom_branch = frappe.db.get_value(doc.voucher_type, doc.voucher_no, "custom_branch")
