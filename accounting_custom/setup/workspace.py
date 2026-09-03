import json

import frappe


OBSOLETE_WORKSPACE_TARGETS = {"Currency Exchange"}


SECTIONS = [
	("Donations and Collectors", [
		("Donation Entry", "DocType"),
		("Collector Profile", "DocType"),
		("Collector Handover", "DocType"),
	]),
	("Payments and Custodies", [
		("Accounting Payment Entry", "DocType"),
		("Accounting Currency Exchange", "DocType"),
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
		("Daily Movement", "Report"),
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
		if row.type == "Card Break" and row.label in section_labels:
			continue
		if row.type == "Link" and (
			row.link_to in custom_targets or row.link_to in OBSOLETE_WORKSPACE_TARGETS
		):
			continue
		existing_links.append(row.as_dict())
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
