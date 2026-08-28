import frappe
from frappe import _


def validate_journal_entry_branch(doc, method=None):
	if not doc.custom_branch:
		frappe.throw(_("Branch is required."))
	branch_company = frappe.db.get_value("Branch", doc.custom_branch, "custom_company")
	if branch_company != doc.company:
		frappe.throw(_("Branch {0} does not belong to company {1}.").format(doc.custom_branch, doc.company))


def set_gl_entry_branch(doc, method=None):
	if not frappe.get_meta("GL Entry").has_field("custom_branch"):
		return
	if doc.get("custom_branch") or not doc.voucher_type or not doc.voucher_no:
		return
	if frappe.get_meta(doc.voucher_type).has_field("custom_branch"):
		doc.custom_branch = frappe.db.get_value(doc.voucher_type, doc.voucher_no, "custom_branch")
