import frappe
from frappe import _
from frappe.model.document import Document


class PayrollReview(Document):
	pass


@frappe.whitelist()
def review(name, action, notes=None):
	doc = frappe.get_doc("Payroll Review", name)
	roles = set(frappe.get_roles())
	if action not in ("Approve", "Return"):
		frappe.throw(_("Invalid review action."))
	if doc.review_status == "Pending CEO":
		if "CEO" not in roles and "System Manager" not in roles:
			frappe.throw(_("CEO role is required."))
		doc.ceo_notes = notes
		if action == "Approve":
			doc.review_status = "Pending President"
			doc.ceo = frappe.session.user
		elif action == "Return":
			doc.review_status = "Returned to Finance"
	elif doc.review_status == "Pending President":
		if "Association President" not in roles and "System Manager" not in roles:
			frappe.throw(_("Association President role is required."))
		doc.president_notes = notes
		if action == "Approve":
			doc.review_status = "Approved"
			doc.president = frappe.session.user
		elif action == "Return":
			doc.review_status = "Returned to Finance"
	elif doc.review_status == "Returned to Finance":
		if "Finance Officer" not in roles and "System Manager" not in roles:
			frappe.throw(_("Finance Officer role is required."))
		if action != "Approve":
			frappe.throw(_("Finance must resubmit the payroll review using Approve."))
		doc.finance_notes = notes
		doc.review_status = "Pending CEO"
	else:
		frappe.throw(_("This payroll review is complete."))
	doc.save(ignore_permissions=True)
	return doc.review_status
