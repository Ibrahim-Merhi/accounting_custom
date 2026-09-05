import frappe

from accounting_custom.setup.workspace import SECTIONS


REQUIRED_DOCTYPES = {
	"Accounting User Guide": {"guide_content"},
	"Collector Profile": {"user", "company", "default_donor_account", "custody_accounts"},
	"Collector Custody Account": {"currency", "account"},
	"Donation Entry": {"collector", "approval_status", "finance_notes", "treasury_status", "reference_no", "journal_entry"},
	"Accounting Payment Entry": {
		"approval_status", "approved_by", "approved_on", "finance_notes", "reference_no", "journal_entry",
	},
	"Accounting Receipt Entry": {
		"company", "posting_date", "reference_no", "custom_accounting_rows_copy",
		"approval_status", "currency_totals", "total_debit", "total_credit", "journal_entry",
	},
	"Accounting Currency Exchange": {"company", "posting_date", "from_mode_of_payment", "source_account", "from_currency", "from_amount", "from_cost_center", "to_mode_of_payment", "target_account", "to_currency", "to_cost_center", "to_amount", "remarks", "journal_entry"},
	"Collector Handover": {"company", "collector", "lines", "received_by"},
	"Collector Handover Detail": {
		"donation_entry", "currency", "amount", "source_account", "destination_account", "cost_center",
	},
	"Payment Memo": {
		"payment_type", "applicant_type", "responsible_manager", "currency", "exchange_rate",
		"allocations", "approval_status", "payment_account", "settlement_against", "ceo_comment",
	},
	"Payment Memo Detail": {"account", "cost_center", "project", "currency", "amount", "invoice"},
	"Employee Monthly Adjustment": {"employee", "payroll_date", "deductions", "total_deductions"},
	"Employee Monthly Adjustment Detail": {"salary_component", "amount", "note"},
	"Payroll Review": {"payroll_entry", "review_status", "ceo_notes", "president_notes"},
	"Payroll Cost Center Allocation": {
		"employee", "salary_structure_assignment", "effective_date", "allocations", "total_percentage",
	},
	"Institution": {"company"},
}

REQUIRED_ROLES = {
	"Collector", "Treasurer", "Finance Officer", "Association President",
	"HR Coordinator", "Responsible Manager", "Volunteer", "Public Relations", "CEO",
}

REQUIRED_REPORTS = {
	"Daily Movement", "Daily Treasury Report", "Collector Collections", "Donor Donation History",
	"Project Donation Summary", "Pending Accounting Approvals", "Open Custodies",
	"Weekly Cost Center Comparison", "Weekly Cash Bank Comparison",
	"Monthly Cost Center Movement", "Monthly Cash Bank Balance",
	"Balance Sheet by Cost Center",
}

REQUIRED_CUSTOM_FIELDS = {
	"Account": {"custom_account_name_arabic", "custom_parent_account_arabic"},
	"Company": {"custom_company_name_arabic"},
	"Cost Center": {
		"custom_cost_center_name_arabic", "custom_parent_cost_center_arabic",
		"custom_company_name_arabic",
	},
	"Donor": {"custom_phone_numper", "custom_accounts"},
	"Journal Entry Account": {"custom_branch"},
	"GL Entry": {"custom_branch"},
}

REQUIRED_PRINT_FORMATS = {
	"سند قبض": "Donation Entry",
	"سند صرف": "Accounting Payment Entry",
	"سند قبض محاسبي": "Accounting Receipt Entry",
	"Journal Voucher": "Journal Entry",
}


@frappe.whitelist()
def verify_accounting_program():
	missing = []
	warnings = []
	for doctype, fields in REQUIRED_DOCTYPES.items():
		if not frappe.db.exists("DocType", doctype):
			missing.append(f"DocType: {doctype}")
			continue
		meta_fields = {field.fieldname for field in frappe.get_meta(doctype).fields}
		for fieldname in sorted(fields - meta_fields):
			missing.append(f"Field: {doctype}.{fieldname}")
	for role in sorted(REQUIRED_ROLES):
		if not frappe.db.exists("Role", role):
			missing.append(f"Role: {role}")
	for report in sorted(REQUIRED_REPORTS):
		if not frappe.db.exists("Report", report):
			missing.append(f"Report: {report}")
	for doctype, fields in REQUIRED_CUSTOM_FIELDS.items():
		meta_fields = {field.fieldname for field in frappe.get_meta(doctype).fields}
		for fieldname in sorted(fields - meta_fields):
			missing.append(f"Custom Field: {doctype}.{fieldname}")
	for print_format, doctype in REQUIRED_PRINT_FORMATS.items():
		actual_doctype = frappe.db.get_value("Print Format", print_format, "doc_type")
		if actual_doctype != doctype:
			missing.append(f"Print Format: {print_format} ({doctype})")
	if not frappe.db.exists("Workspace", "Accounting"):
		missing.append("Workspace: Accounting")
	else:
		workspace_sections = {
			row.label for row in frappe.get_doc("Workspace", "Accounting").links
			if row.type == "Card Break"
		}
		for section, _links in SECTIONS:
			if section not in workspace_sections:
				missing.append(f"Workspace section: Accounting / {section}")
	if frappe.db.exists("Workspace", "Accounting Program"):
		missing.append("Obsolete workspace: Accounting Program")
	if frappe.db.exists("Custom Field", "Supplier-custom_company"):
		missing.append("Obsolete field: Supplier.custom_company")
	if frappe.db.exists("DocType", "Collector Profile") and not frappe.db.count(
		"Collector Profile", {"active": 1}
	):
		warnings.append("No active Collector Profiles are configured yet.")
	if frappe.db.exists("DocType", "Institution") and frappe.db.count("Institution", {"company": ["is", "not set"]}):
		warnings.append("Some Institution records do not have a Company.")
	return {
		"ok": not missing,
		"missing": missing,
		"warnings": warnings,
		"checked_doctypes": len(REQUIRED_DOCTYPES),
		"checked_roles": len(REQUIRED_ROLES),
		"checked_reports": len(REQUIRED_REPORTS),
		"checked_custom_fields": sum(len(fields) for fields in REQUIRED_CUSTOM_FIELDS.values()),
		"checked_print_formats": len(REQUIRED_PRINT_FORMATS),
	}


def assert_accounting_program():
	result = verify_accounting_program()
	if not result["ok"]:
		frappe.throw("Accounting Custom verification failed:\n- " + "\n- ".join(result["missing"]))
	return result
