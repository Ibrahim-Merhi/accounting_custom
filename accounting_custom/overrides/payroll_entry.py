import frappe
from frappe.utils import flt
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry


PROFILE_COMPONENTS = {"Basic Salary", "Transportation", "Family Allowance"}

class CustomPayrollEntry(PayrollEntry):

	def validate_payroll_payable_account(self):
		if not self.get("custom_multi_company_payroll_run"):
			return super().validate_payroll_payable_account()
		account_type = frappe.db.get_value("Account", self.payroll_payable_account, "account_type")
		if account_type != "Payable":
			frappe.throw(f"Payroll payable account {self.payroll_payable_account} must have Account Type Payable.")

	def set_payable_amount_against_payroll_payable_account(self, accounts, currencies, company_currency, accounting_dimensions, precision, payable_amount, payroll_payable_account, employee_wise_accounting_enabled):
		if self.get("custom_multi_company_payroll_run"):
			self.employee_based_payroll_payable_entries = {}
			for slip in frappe.get_all("Salary Slip", filters={"payroll_entry": self.name, "docstatus": 1}, fields=["employee", "net_pay", "salary_structure"]):
				self.employee_based_payroll_payable_entries[slip.employee] = {"earnings": flt(slip.net_pay), "deductions": 0, "salary_structure": slip.salary_structure}
			employee_wise_accounting_enabled = True
		return super().set_payable_amount_against_payroll_payable_account(accounts, currencies, company_currency, accounting_dimensions, precision, payable_amount, payroll_payable_account, employee_wise_accounting_enabled)

	def make_journal_entry(self, accounts, *args, **kwargs):
		if not self.get("custom_multi_company_payroll_run"):
			return super().make_journal_entry(accounts, *args, **kwargs)
		party_amounts = getattr(self, "_profile_party_amounts", {})
		expanded = []
		for row in accounts:
			if row.get("party") or frappe.db.get_value("Account", row.get("account"), "account_type") != "Payable":
				expanded.append(row)
				continue
			matches = [(employee, amount) for (account, cost_center, employee), amount in party_amounts.items() if account == row.get("account") and cost_center == row.get("cost_center")]
			if not matches:
				expanded.append(row)
				continue
			total = sum(flt(amount) for _employee, amount in matches)
			amount_field = "debit_in_account_currency" if row.get("debit_in_account_currency") else "credit_in_account_currency"
			remaining = flt(row.get(amount_field))
			for index, (employee, amount) in enumerate(matches):
				part = remaining if index == len(matches) - 1 else flt(row.get(amount_field)) * flt(amount) / total
				remaining -= part
				child = dict(row)
				child.update({amount_field: part, "party_type": "Employee", "party": employee})
				expanded.append(child)
		return super().make_journal_entry(expanded, *args, **kwargs)

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
					if self.get("custom_multi_company_payroll_run"):
						if not hasattr(self, "_profile_party_amounts"):
							self._profile_party_amounts = {}
						party_key = (allocation.account, allocation.cost_center, item.employee)
						self._profile_party_amounts[party_key] = self._profile_party_amounts.get(party_key, 0) + amount
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
