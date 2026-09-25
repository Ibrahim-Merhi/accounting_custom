import frappe
from frappe import _
from frappe.utils import flt

from accounting_custom.accounting.employee_profile import get_payroll_employee


COMPONENTS = ("Basic Salary", "Transportation", "Family Allowance")


def sync_revision_to_hrms(revision):
	"""Create immutable company-specific HRMS structures and assignments from a salary revision."""
	ensure_salary_components()
	company_amounts = {}
	for row in revision.allocations:
		company_amounts.setdefault(row.company, {}).setdefault(row.component, 0)
		company_amounts[row.company][row.component] += flt(row.amount)
	for company, amounts in company_amounts.items():
		employee = get_payroll_employee(revision.employee, company)
		if not employee:
			frappe.throw(_("No payroll identity exists for employee {0} in company {1}.").format(revision.employee, company))
		create_structure_assignment(revision, employee, company, amounts)


def ensure_salary_components():
	for component in COMPONENTS:
		if frappe.db.exists("Salary Component", component):
			continue
		doc = frappe.get_doc({
			"doctype": "Salary Component", "salary_component": component,
			"salary_component_abbr": "".join(word[0] for word in component.split())[:5].upper(),
			"type": "Earning",
		})
		doc.insert(ignore_permissions=True)


def create_structure_assignment(revision, employee, company, amounts):
	abbr = frappe.db.get_value("Company", company, "abbr") or company[:5]
	currency = frappe.db.get_value("Company", company, "default_currency")
	structure_name = f"Managed-{revision.employee}-{abbr}-R{revision.revision_number}"[:140]
	if not frappe.db.exists("Salary Structure", structure_name):
		structure = frappe.get_doc({
			"doctype": "Salary Structure", "name": structure_name, "company": company,
			"is_active": "Yes", "payroll_frequency": "Monthly", "currency": currency,
		})
		for component in COMPONENTS:
			structure.append("earnings", {
				"salary_component": component, "amount": flt(amounts.get(component)), "amount_based_on_formula": 0,
			})
		structure.flags.ignore_permissions = True
		structure.insert()
		structure.submit()
	if frappe.db.exists("Salary Structure Assignment", {
		"employee": employee, "salary_structure": structure_name, "from_date": revision.effective_from, "docstatus": 1,
	}):
		return
	assignment = frappe.get_doc({
		"doctype": "Salary Structure Assignment", "employee": employee,
		"salary_structure": structure_name, "company": company, "currency": currency,
		"from_date": revision.effective_from, "base": sum(flt(amounts.get(component)) for component in COMPONENTS),
	})
	assignment.flags.ignore_permissions = True
	assignment.insert()
	assignment.submit()
