import frappe

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def ensure_multi_company_payroll_link():
	create_custom_fields({
		"Payroll Entry": [{
			"fieldname": "custom_multi_company_payroll_run",
			"label": "Multi-Company Payroll Run",
			"fieldtype": "Link",
			"options": "Multi Company Payroll Run",
			"insert_after": "payroll_frequency",
			"hidden": 1,
			"read_only": 1,
			"no_copy": 1,
		}],
	}, update=True)
	frappe.db.sql("""
		update `tabPayroll Entry` pe
		inner join `tabMulti Company Payroll Company` company_row on company_row.payroll_entry = pe.name
		set pe.custom_multi_company_payroll_run = company_row.parent
		where coalesce(pe.custom_multi_company_payroll_run, '') = ''
	""")
