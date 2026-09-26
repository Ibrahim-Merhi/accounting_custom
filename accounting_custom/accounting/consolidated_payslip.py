import frappe
from frappe.utils import flt


def sync_consolidated_payslip(master_employee, start_date, end_date):
	identities = frappe.get_all("Employee", filters={"custom_master_employee": master_employee}, pluck="name")
	identities.append(master_employee)
	slips = frappe.get_all(
		"Salary Slip",
		filters={"employee": ["in", list(set(identities))], "start_date": start_date, "end_date": end_date, "docstatus": ["<", 2]},
		fields=["name", "company", "currency", "gross_pay", "total_deduction", "net_pay", "docstatus"],
		order_by="company asc",
	)
	if not slips:
		return None
	currencies = {row.currency for row in slips}
	if len(currencies) != 1:
		return None
	name = f"CPS-{master_employee}-{start_date}-{end_date}"[:140]
	doc = frappe.get_doc("Employee Consolidated Payslip", name) if frappe.db.exists("Employee Consolidated Payslip", name) else frappe.new_doc("Employee Consolidated Payslip")
	doc.payslip_id = name
	doc.employee = master_employee
	doc.employee_name = frappe.db.get_value("Employee", master_employee, "employee_name")
	doc.start_date = start_date
	doc.end_date = end_date
	doc.currency = slips[0].currency
	doc.gross_pay = sum(flt(row.gross_pay) for row in slips)
	doc.total_deduction = sum(flt(row.total_deduction) for row in slips)
	doc.net_pay = sum(flt(row.net_pay) for row in slips)
	doc.company_count = len(slips)
	doc.status = "Submitted" if all(row.docstatus == 1 for row in slips) else "Partial"
	doc.set("companies", [])
	for row in slips:
		doc.append("companies", {"company": row.company, "salary_slip": row.name, "gross_pay": row.gross_pay, "total_deduction": row.total_deduction, "net_pay": row.net_pay, "slip_status": "Submitted" if row.docstatus == 1 else "Draft"})
	doc.flags.ignore_permissions = True
	doc.save()
	return doc.name


def sync_employee_payslips(master_employee):
	identities = frappe.get_all("Employee", filters={"custom_master_employee": master_employee}, pluck="name")
	identities.append(master_employee)
	periods = frappe.get_all("Salary Slip", filters={"employee": ["in", list(set(identities))], "docstatus": ["<", 2]}, fields=["start_date", "end_date"], distinct=True)
	for period in periods:
		sync_consolidated_payslip(master_employee, period.start_date, period.end_date)
	return frappe.get_all("Employee Consolidated Payslip", filters={"employee": master_employee}, fields=["name", "status", "start_date", "end_date", "currency", "gross_pay", "total_deduction", "net_pay", "company_count"], order_by="end_date desc", limit=12)
