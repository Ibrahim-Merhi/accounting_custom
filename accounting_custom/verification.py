import frappe


REQUIRED_DOCTYPES = {
	"Collector Profile": {"user", "company", "default_donor_account", "custody_accounts"},
	"Collector Custody Account": {"currency", "account"},
	"Donation Entry": {"collector", "approval_status", "finance_notes", "treasury_status"},
	"Accounting Payment Entry": {"approval_status", "approved_by", "approved_on", "finance_notes"},
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
	"Daily Treasury Report", "Collector Collections", "Donor Donation History",
	"Project Donation Summary", "Pending Accounting Approvals", "Open Custodies",
	"Weekly Cost Center Comparison", "Weekly Cash Bank Comparison",
	"Monthly Cost Center Movement", "Monthly Cash Bank Balance",
	"Balance Sheet by Cost Center",
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
	if not frappe.db.exists("Workspace", "Accounting Program"):
		missing.append("Workspace: Accounting Program")
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
	}
