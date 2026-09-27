import frappe

from accounting_custom.accounting.consolidated_payslip import sync_consolidated_payslip


def execute():
	for row in frappe.get_all("Employee Consolidated Payslip", fields=["employee", "start_date", "end_date"]):
		sync_consolidated_payslip(row.employee, row.start_date, row.end_date)
