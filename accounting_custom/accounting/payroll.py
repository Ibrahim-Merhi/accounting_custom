import frappe
from frappe import _
from frappe.utils import flt


def validate_payroll_manual_deductions(doc, method=None):
	payroll_employees = {row.employee for row in doc.get("employees") or []}
	for row in doc.get("custom_manual_deductions") or []:
		if row.employee not in payroll_employees:
			frappe.throw(_("Row {0}: Employee must be included in this Payroll Entry.").format(row.idx))
		if frappe.db.get_value("Employee", row.employee, "company") != doc.company:
			frappe.throw(_("Row {0}: Employee must belong to payroll company {1}.").format(row.idx, doc.company))
		if frappe.db.get_value("Salary Component", row.salary_component, "type") != "Deduction":
			frappe.throw(_("Row {0}: Salary Component must be a deduction.").format(row.idx))
		if flt(row.amount) <= 0:
			frappe.throw(_("Row {0}: Deduction amount must be greater than zero.").format(row.idx))


def create_manual_deductions(doc, method=None):
	validate_payroll_manual_deductions(doc)
	for row in doc.get("custom_manual_deductions") or []:
		if row.additional_salary and frappe.db.exists("Additional Salary", row.additional_salary):
			continue
		additional = frappe.get_doc({
			"doctype": "Additional Salary",
			"employee": row.employee,
			"company": doc.company,
			"payroll_date": doc.end_date,
			"salary_component": row.salary_component,
			"amount": row.amount,
			"overwrite_salary_structure_amount": 0,
			"ref_doctype": doc.doctype,
			"ref_docname": doc.name,
		})
		additional.insert(ignore_permissions=True)
		additional.submit()
		row.db_set("additional_salary", additional.name, update_modified=False)


def cancel_manual_deductions(doc, method=None):
	for row in doc.get("custom_manual_deductions") or []:
		if not row.additional_salary or not frappe.db.exists("Additional Salary", row.additional_salary):
			continue
		additional = frappe.get_doc("Additional Salary", row.additional_salary)
		if additional.docstatus == 1:
			additional.cancel()
