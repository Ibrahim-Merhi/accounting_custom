import frappe
from frappe.utils import flt
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry


PROFILE_COMPONENTS = {"Basic Salary", "Transportation", "Family Allowance"}


class CustomPayrollEntry(PayrollEntry):
	def email_salary_slip(self, submitted_ss):
		"""Do not email slips submitted by the custom multi-company payroll run."""
		if self.flags.get("suppress_salary_slip_email"):
			return
		return super().email_salary_slip(submitted_ss)

	def get_salary_component_total(self, component_type=None, employee_wise_accounting_enabled=False):
		if component_type != "earnings":
			return super().get_salary_component_total(component_type, employee_wise_accounting_enabled)
		items = self.get_salary_components(component_type)
		if not items:
			return None
		account_dict = {}
		for item in items:
			allocations = self._profile_allocations(item.employee, item.salary_component)
			if allocations:
				allocation_total = sum(flt(row.amount) for row in allocations)
				for allocation in allocations:
					amount = flt(item.amount) * flt(allocation.amount) / allocation_total
					key = (allocation.account, allocation.cost_center)
					account_dict[key] = account_dict.get(key, 0) + amount
					if employee_wise_accounting_enabled:
						self.set_employee_based_payroll_payable_entries(component_type, item.employee, amount)
				continue
			cost_centers = self.get_payroll_cost_centers_for_employee(item.employee, item.salary_structure)
			for cost_center, percentage in cost_centers.items():
				amount = flt(item.amount) * percentage / 100
				account = self.get_salary_component_account(item.salary_component)
				key = (account, cost_center)
				account_dict[key] = account_dict.get(key, 0) + amount
				if employee_wise_accounting_enabled:
					self.set_employee_based_payroll_payable_entries(component_type, item.employee, amount)
		return account_dict

	def _profile_allocations(self, payroll_employee, component):
		if component not in PROFILE_COMPONENTS:
			return []
		master = frappe.db.get_value("Employee", payroll_employee, "custom_master_employee") or payroll_employee
		revision = frappe.db.sql("""
			select name from `tabEmployee Salary Revision`
			where employee=%s and effective_from <= %s
			and (effective_to is null or effective_to >= %s)
			order by revision_number desc limit 1
		""", (master, self.end_date, self.start_date))
		if not revision:
			return []
		return frappe.get_all("Employee Salary Revision Allocation", filters={
			"parent": revision[0][0], "component": component, "company": self.company,
		}, fields=["account", "cost_center", "amount"], order_by="idx")
