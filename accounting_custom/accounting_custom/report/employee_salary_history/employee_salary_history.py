import frappe
from frappe import _

from accounting_custom.accounting.salary_profile import check_salary_access


def execute(filters=None):
	check_salary_access()
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"fieldname": "employee", "label": _("Employee ID"), "fieldtype": "Link", "options": "Employee", "width": 140},
		{"fieldname": "employee_name", "label": _("Employee Name"), "width": 180},
		{"fieldname": "revision_number", "label": _("Revision"), "fieldtype": "Int", "width": 80},
		{"fieldname": "effective_from", "label": _("Effective From"), "fieldtype": "Date", "width": 110},
		{"fieldname": "effective_to", "label": _("Effective To"), "fieldtype": "Date", "width": 110},
		{"fieldname": "action_date", "label": _("Action Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "component", "label": _("Salary Component"), "width": 150},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 170},
		{"fieldname": "account", "label": _("Account"), "fieldtype": "Link", "options": "Account", "width": 220},
		{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center", "width": 220},
		{"fieldname": "percentage", "label": _("Percentage"), "fieldtype": "Percent", "width": 100},
		{"fieldname": "amount", "label": _("Allocated Amount"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "total_salary", "label": _("Total Salary"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "changed_by", "label": _("Changed By"), "fieldtype": "Link", "options": "User", "width": 180},
		{"fieldname": "change_summary", "label": _("Change Summary"), "width": 300},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.employee:
		conditions.append("r.employee = %(employee)s")
		values["employee"] = filters.employee
	if filters.company:
		conditions.append("a.company = %(company)s")
		values["company"] = filters.company
	if filters.from_date:
		conditions.append("r.effective_from >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.to_date:
		conditions.append("r.effective_from <= %(to_date)s")
		values["to_date"] = filters.to_date
	where = " and " + " and ".join(conditions) if conditions else ""
	return frappe.db.sql(f"""
		select r.employee, r.employee_name, r.revision_number, r.effective_from,
			r.effective_to, r.action_date, a.component, a.company, a.account,
			a.cost_center, a.percentage, a.amount, r.total_salary, r.changed_by,
			r.change_summary
		from `tabEmployee Salary Revision` r
		left join `tabEmployee Salary Revision Allocation` a on a.parent = r.name
		where r.docstatus < 2 {where}
		order by r.employee_name, r.revision_number desc, a.idx
	""", values, as_dict=True)
