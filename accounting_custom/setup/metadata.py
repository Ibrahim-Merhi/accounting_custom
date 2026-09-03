import frappe


PRINT_FORMATS = {
"سند قبض": "Donation Entry",
	"سند صرف": "Accounting Payment Entry",
	"Journal Voucher": "Journal Entry",
}

REPORTS = {
	"Balance Sheet by Cost Center": "GL Entry",
	"Collector Collections": "Donation Entry",
	"Daily Movement": "GL Entry",
	"Daily Treasury Report": "Accounting Payment Entry",
	"Donor Donation History": "Donation Entry",
	"Monthly Cash Bank Balance": "GL Entry",
	"Monthly Cost Center Movement": "GL Entry",
	"Open Custodies": "Payment Memo",
	"Pending Accounting Approvals": "Payment Memo",
	"Project Donation Summary": "Donation Entry",
	"Weekly Cash Bank Comparison": "GL Entry",
	"Weekly Cost Center Comparison": "GL Entry",
}


def ensure_visible_metadata():
	"""Keep app-owned formats and reports visible in their standard list views."""
	for name, doc_type in PRINT_FORMATS.items():
		if frappe.db.exists("Print Format", name):
			frappe.db.set_value(
				"Print Format",
				name,
				{
					"doc_type": doc_type,
					"module": "Accounting Custom",
					"disabled": 0,
				},
				update_modified=False,
			)

	for name, ref_doctype in REPORTS.items():
		if frappe.db.exists("Report", name):
			frappe.db.set_value(
				"Report",
				name,
				{
					"report_name": name,
					"ref_doctype": ref_doctype,
					"module": "Accounting Custom",
					"report_type": "Script Report",
					"is_standard": "Yes",
					"disabled": 0,
				},
				update_modified=False,
			)

	frappe.clear_cache(doctype="Print Format")
	frappe.clear_cache(doctype="Report")
