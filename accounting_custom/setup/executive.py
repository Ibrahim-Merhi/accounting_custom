import json

import frappe
from frappe.permissions import add_permission, update_permission_property


ROLE = "Group CEO"
WORKSPACE = "Group CEO Dashboard"
PAGE = "group-ceo-dashboard"

READ_ONLY_DOCTYPES = (
	"Company", "Account", "GL Entry", "Cost Center", "Budget", "Bank Account",
	"Journal Entry", "Payment Entry", "Sales Invoice", "Purchase Invoice",
	"Sales Order", "Purchase Order", "Customer", "Supplier", "Item", "Project",
	"Employee", "Department", "Branch", "Designation", "Employment Type",
	"Holiday List", "Shift Type", "Leave Type", "Leave Allocation", "Leave Application",
	"Attendance", "Salary Slip", "Payroll Entry", "Payroll Review", "Salary Structure",
	"Salary Component", "Additional Salary",
	"Employee Salary Profile", "Employee Consolidated Payslip", "Employee Advance",
	"Donor", "Donor Type", "Donation", "Donation Entry", "Multi Donation", "Collector Handover",
	"Accounting Payment Entry", "Accounting Receipt Entry", "Custodies",
	"Beneficiary", "Beneficiary Group", "Family", "Beneficiary Evaluation", "Beneficiary Activity",
	"Relief Entry", "Relief Order", "Relief Statement", "Material Donation",
)

REPORT_MODULES = {
	"Accounts", "HR", "Payroll", "Accounting Custom", "Non Profit", "Relief Management",
}

NUMBER_CARDS = (
	("Group CEO Active Employees", "Active Employees", "active_employees", "#169b62", "Employee"),
	("Group CEO Pending Leaves", "Pending Leaves", "pending_leaves", "#e09b25", "Leave Application"),
	("Group CEO Attendance Today", "Attendance Today", "attendance_today", "#3977c3", "Attendance"),
	("Group CEO Payroll YTD", "Payroll YTD", "payroll_ytd", "#7a5bd6", "Salary Slip"),
	("Group CEO Donors", "Donors", "donors", "#cf657f", "Donor"),
	("Group CEO Beneficiaries", "Beneficiaries", "beneficiaries", "#0c9b9b", "Beneficiary"),
	("Group CEO Families", "Families", "families", "#d27636", "Family"),
	("Group CEO Relief Orders", "Relief Orders", "relief_orders", "#5268ad", "Relief Order"),
)


def ensure_group_ceo_experience():
	_ensure_role()
	_ensure_permissions()
	_ensure_report_access()
	_ensure_number_cards()
	_ensure_workspace()
	_sync_existing_users()


def _ensure_role():
	if not frappe.db.exists("Role", ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 1}).insert(ignore_permissions=True)


def _ensure_permissions():
	for doctype in READ_ONLY_DOCTYPES:
		if not frappe.db.exists("DocType", doctype) or frappe.get_meta(doctype).istable:
			continue
		filters = {"parent": doctype, "role": ROLE, "permlevel": 0, "if_owner": 0}
		if not frappe.db.exists("Custom DocPerm", filters):
			add_permission(doctype, ROLE, 0, "read")
		for permission in ("read", "report", "export", "print"):
			update_permission_property(doctype, ROLE, 0, permission, 1, validate=False)
		for permission in ("write", "create", "delete", "submit", "cancel", "amend", "import", "email", "share"):
			update_permission_property(doctype, ROLE, 0, permission, 0, validate=False)
		frappe.clear_cache(doctype=doctype)


def _ensure_report_access():
	for row in frappe.get_all("Report", filters={"module": ["in", list(REPORT_MODULES)]}, fields=["name"]):
		roles = frappe.get_all(
			"Has Role",
			filters={"parent": row.name, "parenttype": "Report", "parentfield": "roles"},
			pluck="role",
		)
		# An empty roles table means the report is already available to every
		# permitted user. Do not turn an unrestricted report into a CEO-only one.
		if roles and ROLE not in roles:
			# Insert only the child permission row. Resaving a legacy Report can
			# fail on unrelated stale links (for example, a deleted Letter Head).
			frappe.get_doc({
				"doctype": "Has Role",
				"parent": row.name,
				"parenttype": "Report",
				"parentfield": "roles",
				"role": ROLE,
			}).insert(ignore_permissions=True)


def _ensure_number_cards():
	for name, label, metric, color, document_type in NUMBER_CARDS:
		values = {
			"label": label, "type": "Custom", "method": "accounting_custom.executive.number_card",
			"filters_json": json.dumps({"metric": metric}), "is_public": 0,
			"show_percentage_stats": 0, "color": color, "document_type": document_type,
		}
		if frappe.db.exists("Number Card", name):
			frappe.db.set_value("Number Card", name, values, update_modified=False)
		else:
			frappe.get_doc({"doctype": "Number Card", "name": name, **values}).insert(ignore_permissions=True)


def _ensure_workspace():
	content = [{"id": "group_ceo_title", "type": "header", "data": {"text": '<span class="h4"><b>Group Executive Overview</b></span>', "col": 12}}]
	for index, (name, _label, _metric, _color, _document_type) in enumerate(NUMBER_CARDS, 1):
		content.append({"id": f"group_ceo_metric_{index}", "type": "number_card", "data": {"number_card_name": name, "col": 3}})
	content.extend([
		{"id": "group_ceo_insights_header", "type": "header", "data": {"text": '<span class="h4"><b>Executive Analytics</b></span>', "col": 12}},
		{"id": "group_ceo_insights", "type": "shortcut", "data": {"shortcut_name": "Open Executive Dashboard", "col": 4}},
		{"id": "group_ceo_reports", "type": "card", "data": {"card_name": "Executive Reports", "col": 8}},
	])
	values = {"label": WORKSPACE, "title": WORKSPACE, "module": "Accounting Custom", "icon": "organization", "public": 1, "is_hidden": 0, "content": json.dumps(content, separators=(",", ":"))}
	exists = frappe.db.exists("Workspace", WORKSPACE)
	doc = frappe.get_doc("Workspace", WORKSPACE) if exists else frappe.get_doc({"doctype": "Workspace", "name": WORKSPACE})
	for key, value in values.items():
		setattr(doc, key, value)
	doc.set("roles", [{"role": ROLE}])
	doc.set("number_cards", [{"number_card_name": item[0], "label": item[1]} for item in NUMBER_CARDS])
	doc.set("shortcuts", [{"label": "Open Executive Dashboard", "type": "Page", "link_to": PAGE, "color": "Blue"}])
	doc.set("links", _report_links())
	doc.flags.ignore_permissions = True
	developer_mode = frappe.conf.developer_mode
	try:
		frappe.conf.developer_mode = 0
		doc.save() if exists else doc.insert(ignore_permissions=True)
	finally:
		frappe.conf.developer_mode = developer_mode
	frappe.clear_cache(doctype="Workspace")


def _report_links():
	sections = {
		"HR and Payroll": ("Employee", "Leave Application", "Attendance", "Salary Slip", "Payroll Entry", "Employee Salary History"),
		"Accounting": ("General Ledger", "Trial Balance", "Balance Sheet", "Profit and Loss Statement", "Daily Treasury Report", "Monthly Cash Bank Balance", "Balance Sheet by Cost Center"),
		"Donations": ("Donation Entry", "Donor", "Donor Donation History", "Collector Collections", "Project Donation Summary"),
		"Relief Management": ("Beneficiary", "Family", "Relief Order", "Relief Statement", "Beneficiary-wise Sponsors", "Sponsor-wise Beneficiary", "Orphan Balance", "Donation Report"),
	}
	result = []
	for section, targets in sections.items():
		result.append({"type": "Card Break", "label": section})
		for target in targets:
			link_type = "Report" if frappe.db.exists("Report", target) else "DocType"
			if link_type == "DocType" and not frappe.db.exists("DocType", target):
				continue
			result.append({"type": "Link", "label": target, "link_type": link_type, "link_to": target, "is_query_report": 1 if link_type == "Report" else 0})
	return result


def _sync_existing_users():
	users = frappe.get_all("Has Role", filters={"role": ROLE, "parenttype": "User"}, pluck="parent")
	for user in users:
		if user not in ("Administrator", "Guest"):
			frappe.db.set_value("User", user, "default_workspace", WORKSPACE, update_modified=False)


def set_group_ceo_default_workspace(doc, method=None):
	if doc.name not in ("Administrator", "Guest") and ROLE in {row.role for row in doc.roles} and doc.default_workspace != WORKSPACE:
		frappe.db.set_value("User", doc.name, "default_workspace", WORKSPACE, update_modified=False)
