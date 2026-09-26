import frappe
from frappe import _
from frappe.utils import flt

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry


PROFILE_COMPONENTS = {"Basic Salary", "Transportation", "Family Allowance"}

class CustomPayrollEntry(PayrollEntry):

	def _is_managed_payroll(self):
		if self.get("custom_multi_company_payroll_run"):
			return True
		employees = [row.employee for row in self.get("employees") if row.employee]
		if not employees:
			employees = frappe.get_all("Salary Slip", filters={"payroll_entry": self.name}, pluck="employee")
		if not employees:
			return False
		return bool(frappe.db.sql("""
			select 1 from `tabSalary Structure Assignment`
			where employee in %(employees)s and salary_structure like 'Managed-%%'
			and docstatus = 1 and from_date <= %(end_date)s limit 1
		""", {"employees": tuple(set(employees)), "end_date": self.end_date}))

	def validate_payroll_payable_account(self):
		if not self._is_managed_payroll():
			return super().validate_payroll_payable_account()
		account_type = frappe.db.get_value("Account", self.payroll_payable_account, "account_type")
		if account_type != "Payable":
			frappe.throw(f"Payroll payable account {self.payroll_payable_account} must have Account Type Payable.")

	def set_payable_amount_against_payroll_payable_account(self, accounts, currencies, company_currency, accounting_dimensions, precision, payable_amount, payroll_payable_account, employee_wise_accounting_enabled):
		if not self._is_managed_payroll():
			return super().set_payable_amount_against_payroll_payable_account(accounts, currencies, company_currency, accounting_dimensions, precision, payable_amount, payroll_payable_account, employee_wise_accounting_enabled)

		self.employee_based_payroll_payable_entries = {}
		party_amounts = getattr(self, "_profile_party_amounts", {})
		slips = frappe.get_all("Salary Slip", filters={"payroll_entry": self.name, "docstatus": 1}, fields=["employee", "net_pay", "salary_structure"])
		for slip in slips:
			net_pay = flt(slip.net_pay)
			self.employee_based_payroll_payable_entries[slip.employee] = {"earnings": net_pay, "deductions": 0, "salary_structure": slip.salary_structure}
			cost_centers = {}
			for (_account, cost_center, employee), amount in party_amounts.items():
				if employee == slip.employee:
					cost_centers[cost_center] = cost_centers.get(cost_center, 0) + flt(amount)
			if not cost_centers:
				cost_centers = {self.cost_center: net_pay}
			total_weight = sum(cost_centers.values())
			remaining = net_pay
			for index, (cost_center, weight) in enumerate(sorted(cost_centers.items())):
				amount = remaining if index == len(cost_centers) - 1 else flt(net_pay * weight / total_weight, precision)
				remaining -= amount
				self.get_accounting_entries_and_payable_amount(
					payroll_payable_account, cost_center, amount, currencies, company_currency, 0,
					accounting_dimensions, precision, entry_type="payable", party=slip.employee, accounts=accounts,
				)
		return None

	def set_accounting_entries_for_bank_entry(self, je_payment_amount, user_remark):
		rows = self.get("custom_bank_payment_allocations") or []
		if not self._is_managed_payroll() or not rows:
			return super().set_accounting_entries_for_bank_entry(je_payment_amount, user_remark)

		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
		company_currency = erpnext.get_company_currency(self.company)
		accounting_dimensions = get_accounting_dimensions() or []
		currencies = []
		payment_groups = {}
		for row in rows:
			account = frappe.db.get_value(
				"Account", row.payment_account,
				["company", "account_type", "is_group", "disabled"], as_dict=True,
			)
			if not account or account.company != self.company or account.is_group or account.disabled:
				frappe.throw(_("Row {0}: select an enabled ledger account belonging to {1}.").format(row.idx, self.company))
			if account.account_type not in ("Bank", "Cash"):
				frappe.throw(_("Row {0}: payment account must have Account Type Bank or Cash.").format(row.idx))
			if frappe.db.get_value("Cost Center", row.cost_center, "company") != self.company:
				frappe.throw(_("Row {0}: cost center must belong to {1}.").format(row.idx, self.company))
			if flt(row.amount) <= 0:
				frappe.throw(_("Row {0}: amount must be greater than zero.").format(row.idx))
			key = (row.payment_account, row.cost_center)
			payment_groups[key] = payment_groups.get(key, 0) + flt(row.amount)

		payment_total = sum(payment_groups.values())
		if abs(payment_total - flt(je_payment_amount)) > 0.01:
			frappe.throw(_("Bank / Cash allocation total {0} must equal net payroll {1}.").format(payment_total, je_payment_amount))

		payable_rows = self._get_managed_payable_rows(precision)
		payable_by_cost_center = {}
		for row in payable_rows:
			payable_by_cost_center[row.cost_center] = payable_by_cost_center.get(row.cost_center, 0) + row.amount
		payment_by_cost_center = {}
		for (_account, cost_center), amount in payment_groups.items():
			payment_by_cost_center[cost_center] = payment_by_cost_center.get(cost_center, 0) + amount
		if any(abs(payable_by_cost_center.get(cost_center, 0) - payment_by_cost_center.get(cost_center, 0)) > 0.01 for cost_center in set(payable_by_cost_center) | set(payment_by_cost_center)):
			frappe.throw(_("Bank / Cash amounts must match the net payroll amount for each cost center."))

		accounts = []
		for (payment_account, cost_center), payment_amount in sorted(payment_groups.items()):
			exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
				payment_account, payment_amount, company_currency, currencies
			)
			accounts.append(self.update_accounting_dimensions({
				"account": payment_account,
				"credit_in_account_currency": flt(amount, precision),
				"exchange_rate": flt(exchange_rate),
				"cost_center": cost_center,
			}, accounting_dimensions))

		for payable in payable_rows:
			exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
				self.payroll_payable_account, payable.amount, company_currency, currencies
			)
			accounts.append(self.update_accounting_dimensions({
				"account": self.payroll_payable_account,
				"debit_in_account_currency": flt(amount, precision),
				"exchange_rate": flt(exchange_rate),
				"reference_type": self.doctype,
				"reference_name": self.name,
				"party_type": "Employee",
				"party": payable.employee,
				"cost_center": payable.cost_center,
			}, accounting_dimensions))

		self.make_journal_entry(
			accounts, currencies, voucher_type="Bank Entry",
			user_remark=_("Payment of {0} from {1} to {2}").format(user_remark, self.start_date, self.end_date),
		)

	def _get_managed_payable_rows(self, precision):
		rows = []
		slips = frappe.get_all(
			"Salary Slip", filters={"payroll_entry": self.name, "docstatus": 1},
			fields=["employee", "net_pay"], order_by="employee",
		)
		for slip in slips:
			weights = {}
			for component in PROFILE_COMPONENTS:
				for allocation in self._profile_allocations(slip.employee, component):
					weights[allocation.cost_center] = weights.get(allocation.cost_center, 0) + flt(allocation.amount)
			if not weights:
				weights = {self.cost_center: flt(slip.net_pay)}
			total_weight = sum(weights.values())
			remaining = flt(slip.net_pay)
			for index, (cost_center, weight) in enumerate(sorted(weights.items())):
				amount = remaining if index == len(weights) - 1 else flt(flt(slip.net_pay) * weight / total_weight, precision)
				remaining -= amount
				rows.append(frappe._dict(employee=slip.employee, cost_center=cost_center, amount=amount))
		return rows

	def make_journal_entry(self, accounts, *args, **kwargs):
		if not self._is_managed_payroll():
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
		"""Custom multi-company payroll keeps slips in-app and never emails them."""
		if self._is_managed_payroll() or self.flags.get("suppress_salary_slip_email"):
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
					if self._is_managed_payroll():
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
