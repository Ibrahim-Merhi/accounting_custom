import json

import frappe


OBSOLETE_WORKSPACE_TARGETS = {
	"Currency Exchange", "Daily Movement", "Daily Movement Other Currency",
}

CUSTOM_REPORTS_SECTION = "Custom Reports"
ACCOUNT_COST_CENTER_REPORT = "Account and Cost Center Report"
ANALYTICAL_TRIAL_BALANCE = "Analytical Trial Balance"

HR_NUMBER_CARDS = (
	("HR Active Employees", "Active Employees", "Employee", [["status", "=", "Active"]], []),
	("HR Present Today", "Present Today", "Attendance", [["status", "=", "Present"], ["docstatus", "=", 1]], [["attendance_date", "=", "frappe.datetime.get_today()"]]),
	("HR Absent Today", "Absent Today", "Attendance", [["status", "=", "Absent"], ["docstatus", "=", 1]], [["attendance_date", "=", "frappe.datetime.get_today()"]]),
	("HR On Leave Today", "Employees on Leave Today", "Attendance", [["status", "=", "On Leave"], ["docstatus", "=", 1]], [["attendance_date", "=", "frappe.datetime.get_today()"]]),
	("HR New Employees This Month", "New Employees This Month", "Employee", [], [["date_of_joining", ">=", "frappe.datetime.month_start()"], ["date_of_joining", "<=", "frappe.datetime.month_end()"]]),
	("HR Employees Leaving Soon", "Employees Leaving Soon", "Employee", [["status", "=", "Active"]], [["relieving_date", ">=", "frappe.datetime.get_today()"], ["relieving_date", "<=", "frappe.datetime.add_days(frappe.datetime.get_today(), 30)"]]),
	("HR Pending Leave Applications", "Pending Leave Applications", "Leave Application", [["status", "=", "Open"], ["docstatus", "=", 0]], []),
	("HR Pending Expense Claims", "Pending Expense Claims", "Expense Claim", [["approval_status", "=", "Draft"], ["docstatus", "=", 0]], []),
)

HR_CHARTS = (
	"Employees by Branch", "Department Wise Employee Count", "Attendance Count",
	"HR Leave Distribution", "Hiring vs Attrition Count", "Outgoing Salary",
	"Department Wise Salary(Last Month)",
)

HR_SHORTCUTS = (
	("Employee", "DocType"), ("Attendance", "DocType"),
	("Leave Application", "DocType"), ("Salary Slip", "DocType"),
	("Payroll Entry", "DocType"), ("Shift Assignment", "DocType"),
	("Employee Monthly Adjustment", "DocType"),
	("Payroll Cost Center Allocation", "DocType"),
)

HR_REPORTS = (
	"Monthly Attendance Sheet", "Employee Leave Balance", "Salary Register",
	"Employee Analytics", "Employee Information",
)


SECTIONS = [
	("Donations and Collectors", [
		("Donation Entry", "DocType"),
		("Collector Profile", "DocType"),
		("Collector Handover", "DocType"),
	]),
	("Payments and Custodies", [
		("Accounting Payment Entry", "DocType"),
		("Accounting Receipt Entry", "DocType"),
		("Accounting Currency Exchange", "DocType"),
		("Custodies", "DocType"),
		("Party Type", "DocType"),
		("Payment Memo", "DocType"),
	]),
	("Payroll", [
		("Payroll Cost Center Allocation", "DocType"),
		("Employee Monthly Adjustment", "DocType"),
		("Payroll Review", "DocType"),
	]),
	("Accounting Setup", [
		("Accounting User Guide", "DocType"),
		("Company Exchange Rate", "DocType"),
		("Institution", "DocType"),
	]),
	("Donation Reports", [
		("Collector Collections", "Report"),
		("Donor Donation History", "Report"),
		("Project Donation Summary", "Report"),
	]),
	("Treasury and Approval Reports", [
		("All Daily Movement", "Report"),
		("Daily Treasury Report", "Report"),
		("Pending Accounting Approvals", "Report"),
		("Open Custodies", "Report"),
	]),
	("Weekly Financial Reports", [
		("Weekly Cost Center Comparison", "Report"),
		("Weekly Cash Bank Comparison", "Report"),
	]),
	("Monthly and Cost Center Reports", [
		("Monthly Cost Center Movement", "Report"),
		("Monthly Cash Bank Balance", "Report"),
		("Balance Sheet by Cost Center", "Report"),
	]),
]


def ensure_accounting_workspace_sections():
	if not frappe.db.exists("Workspace", "Accounting"):
		return

	doc = frappe.get_doc("Workspace", "Accounting")
	if "Treasurer" not in {row.role for row in doc.roles}:
		doc.append("roles", {"role": "Treasurer"})
	content = json.loads(doc.content or "[]")
	content = [item for item in content if not item.get("id", "").startswith("accounting_custom_")]
	has_custom_reports_card = any(
		item.get("type") == "card"
		and item.get("data", {}).get("card_name") == CUSTOM_REPORTS_SECTION
		for item in content
	)
	if not has_custom_reports_card:
		content.append({
			"id": "accounting_custom_custom_reports_card",
			"type": "card",
			"data": {"card_name": CUSTOM_REPORTS_SECTION, "col": 4},
		})
	content.extend([
		{
			"id": "accounting_custom_header",
			"type": "header",
			"data": {"text": '<span class="h4"><b>Accounting Operations and Reports</b></span>', "col": 12},
		}
	])
	for index, (section, _links) in enumerate(SECTIONS, 1):
		content.append({
			"id": f"accounting_custom_card_{index}",
			"type": "card",
			"data": {"card_name": section, "col": 4},
		})
	doc.content = json.dumps(content, separators=(",", ":"))

	section_labels = {section for section, _links in SECTIONS}
	custom_targets = {label for _section, links in SECTIONS for label, _link_type in links}
	existing_links = []
	for row in doc.links:
		if row.type == "Link" and row.link_to == ACCOUNT_COST_CENTER_REPORT:
			continue
		if row.type == "Card Break" and row.label in section_labels:
			continue
		if row.type == "Link" and (
			row.link_to in custom_targets or row.link_to in OBSOLETE_WORKSPACE_TARGETS
		):
			continue
		existing_links.append(row.as_dict())

	custom_reports_index = next(
		(
			index for index, row in enumerate(existing_links)
			if row.get("type") == "Card Break" and row.get("label") == CUSTOM_REPORTS_SECTION
		),
		None,
	)
	if custom_reports_index is None:
		existing_links.append({"type": "Card Break", "label": CUSTOM_REPORTS_SECTION})
		custom_reports_index = len(existing_links) - 1

	insert_at = custom_reports_index + 1
	for index in range(custom_reports_index + 1, len(existing_links)):
		row = existing_links[index]
		if row.get("type") == "Card Break":
			break
		if row.get("type") == "Link" and row.get("link_to") == ANALYTICAL_TRIAL_BALANCE:
			insert_at = index
			break
		insert_at = index + 1
	existing_links.insert(insert_at, {
		"type": "Link",
		"label": ACCOUNT_COST_CENTER_REPORT,
		"link_type": "Report",
		"link_to": ACCOUNT_COST_CENTER_REPORT,
		"is_query_report": 1,
	})
	doc.set("links", existing_links)

	for section, links in SECTIONS:
		doc.append("links", {"type": "Card Break", "label": section})
		for label, link_type in links:
				doc.append("links", {
				"type": "Link", "label": label, "link_type": link_type,
				"link_to": label, "is_query_report": 1 if link_type == "Report" else 0,
			})
	for index, row in enumerate(doc.links, 1):
		row.idx = index

	doc.flags.ignore_permissions = True
	developer_mode = frappe.conf.developer_mode
	try:
		# This is a database overlay owned by accounting_custom. Do not export the
		# modified standard workspace into ERPNext when the site is in developer mode.
		frappe.conf.developer_mode = 0
		doc.save()
	finally:
		frappe.conf.developer_mode = developer_mode
	frappe.clear_cache(doctype="Workspace")


def ensure_hr_manager_workspace():
	"""Add an app-managed HR manager dashboard to the standard HR workspace."""
	if not frappe.db.exists("Workspace", "HR"):
		return

	card_names = _ensure_hr_number_cards()
	_ensure_hr_leave_distribution_chart()
	doc = frappe.get_doc("Workspace", "HR")
	content = [item for item in json.loads(doc.content or "[]") if not item.get("id", "").startswith("accounting_custom_hr_")]
	managed_content = [{"id": "accounting_custom_hr_header", "type": "header", "data": {"text": "<span class=\"h4\"><b>HR Manager Dashboard</b></span>", "col": 12}}]
	for index, (name, *_rest) in enumerate(HR_NUMBER_CARDS, 1):
		managed_content.append({"id": f"accounting_custom_hr_number_{index}", "type": "number_card", "data": {"number_card_name": card_names[name], "col": 3}})
	managed_content.extend([
		{"id": "accounting_custom_hr_spacer_1", "type": "spacer", "data": {"col": 12}},
		{"id": "accounting_custom_hr_analytics_header", "type": "header", "data": {"text": "<span class=\"h4\"><b>HR Analytics</b></span>", "col": 12}},
	])
	for index, chart_name in enumerate(HR_CHARTS, 1):
		managed_content.append({"id": f"accounting_custom_hr_chart_{index}", "type": "chart", "data": {"chart_name": chart_name, "col": 6}})
	managed_content.extend([
		{"id": "accounting_custom_hr_spacer_2", "type": "spacer", "data": {"col": 12}},
		{"id": "accounting_custom_hr_shortcuts_header", "type": "header", "data": {"text": "<span class=\"h4\"><b>HR Operations</b></span>", "col": 12}},
	])
	for index, (label, _link_type) in enumerate(HR_SHORTCUTS, 1):
		managed_content.append({"id": f"accounting_custom_hr_shortcut_{index}", "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
	managed_content.extend([
		{"id": "accounting_custom_hr_spacer_3", "type": "spacer", "data": {"col": 12}},
		{"id": "accounting_custom_hr_reports_header", "type": "header", "data": {"text": "<span class=\"h4\"><b>HR Manager Reports</b></span>", "col": 12}},
		{"id": "accounting_custom_hr_reports_card", "type": "card", "data": {"card_name": "HR Manager Reports", "col": 4}},
	])
	doc.content = json.dumps(managed_content + content, separators=(",", ":"))

	managed_cards = set(card_names.values())
	doc.set("number_cards", [row.as_dict() for row in doc.number_cards if row.number_card_name not in managed_cards])
	for configured_name, label, *_rest in HR_NUMBER_CARDS:
		name = card_names[configured_name]
		doc.append("number_cards", {"number_card_name": name, "label": label})
	doc.set("charts", [row.as_dict() for row in doc.charts if row.chart_name not in HR_CHARTS])
	for chart_name in HR_CHARTS:
		if frappe.db.exists("Dashboard Chart", chart_name):
			doc.append("charts", {"chart_name": chart_name, "label": chart_name})

	managed_shortcuts = {label for label, _link_type in HR_SHORTCUTS}
	doc.set("shortcuts", [row.as_dict() for row in doc.shortcuts if row.label not in managed_shortcuts])
	for label, link_type in HR_SHORTCUTS:
		if frappe.db.exists(link_type, label):
			doc.append("shortcuts", {"label": label, "type": link_type, "link_to": label, "doc_view": "List" if link_type == "DocType" else ""})

	managed_link_targets = set(HR_REPORTS)
	links = [row.as_dict() for row in doc.links if not ((row.type == "Card Break" and row.label == "HR Manager Reports") or (row.type == "Link" and row.link_to in managed_link_targets))]
	links.append({"type": "Card Break", "label": "HR Manager Reports"})
	for report in HR_REPORTS:
		if frappe.db.exists("Report", report):
			links.append({"type": "Link", "label": report, "link_type": "Report", "link_to": report, "is_query_report": 1})
	doc.set("links", links)
	_save_workspace_overlay(doc)


def _ensure_hr_number_cards():
	card_names = {}
	company_filter = ["company", "=", "frappe.defaults.get_user_default(\"Company\")"]
	for name, label, document_type, filters, dynamic_filters in HR_NUMBER_CARDS:
		values = {
			"label": label, "type": "Document Type", "document_type": document_type, "function": "Count",
			"filters_json": json.dumps([[document_type, *item, False] for item in filters]),
			"dynamic_filters_json": json.dumps([[document_type, *company_filter], *[[document_type, *item] for item in dynamic_filters]]),
			"is_public": 1, "is_standard": 0, "module": "Accounting Custom", "show_percentage_stats": 0,
		}
		existing_name = frappe.db.get_value("Number Card", {"label": label, "module": "Accounting Custom"}, "name")
		if existing_name:
			doc = frappe.get_doc("Number Card", existing_name)
			doc.update(values)
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc({"doctype": "Number Card", **values})
			doc.name = name
			doc.insert(ignore_permissions=True)
		card_names[name] = doc.name
	return card_names


def _ensure_hr_leave_distribution_chart():
	name = "HR Leave Distribution"
	values = {
		"chart_name": name, "chart_type": "Group By", "document_type": "Leave Application",
		"filters_json": json.dumps([["Leave Application", "docstatus", "=", 1, False]]),
		"dynamic_filters_json": json.dumps([["Leave Application", "company", "=", "frappe.defaults.get_user_default(\"Company\")"]]),
		"group_by_based_on": "leave_type", "group_by_type": "Count", "is_public": 1,
		"is_standard": 0, "module": "Accounting Custom", "timeseries": 0, "type": "Donut", "use_report_chart": 0,
	}
	if frappe.db.exists("Dashboard Chart", name):
		doc = frappe.get_doc("Dashboard Chart", name)
		doc.update(values)
		doc.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "Dashboard Chart", "name": name, **values}).insert(ignore_permissions=True)


def _save_workspace_overlay(doc):
	for table in (doc.links, doc.shortcuts, doc.charts, doc.number_cards):
		for index, row in enumerate(table, 1):
			row.idx = index
	doc.flags.ignore_permissions = True
	developer_mode = frappe.conf.developer_mode
	try:
		frappe.conf.developer_mode = 0
		doc.save()
	finally:
		frappe.conf.developer_mode = developer_mode
	frappe.clear_cache(doctype="Workspace")


def remove_standalone_accounting_program_workspace():
	if not frappe.db.exists("Workspace", "Accounting Program"):
		return
	developer_mode = frappe.conf.developer_mode
	try:
		frappe.conf.developer_mode = 0
		frappe.delete_doc("Workspace", "Accounting Program", ignore_permissions=True, force=True)
	finally:
		frappe.conf.developer_mode = developer_mode
	frappe.clear_cache(doctype="Workspace")
