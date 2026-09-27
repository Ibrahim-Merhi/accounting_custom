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
		for row in self._get_managed_payable_rows(precision):
			self.get_accounting_entries_and_payable_amount(
				payroll_payable_account, row.cost_center, row.amount, currencies, company_currency, 0,
				accounting_dimensions, precision, entry_type="payable", party=row.employee, accounts=accounts,
			)
		return None
	def get_outstanding_payable_rows(self, precision=2):
		paid = {}
		for row in frappe.db.sql("""select a.party as employee, a.cost_center, sum(a.debit_in_account_currency) amount from `tabJournal Entry Account` a join `tabJournal Entry` j on j.name=a.parent where j.docstatus=1 and j.voucher_type='Bank Entry' and a.reference_type='Payroll Entry' and a.reference_name=%s and a.account=%s group by a.party, a.cost_center""", (self.name, self.payroll_payable_account), as_dict=True):
			paid[(row.employee, row.cost_center)] = flt(row.amount)
		result = []
		for row in self._get_managed_payable_rows(precision):
			amount = flt(row.amount) - paid.get((row.employee, row.cost_center), 0)
			if amount > 0.01:
				result.append(frappe._dict({"employee": row.employee, "cost_center": row.cost_center, "amount": round(flt(amount), int(precision))}))
		return result

	@frappe.whitelist()
	def get_bank_payment_allocation_defaults(self):
		self.check_permission("read")
		if not self._is_managed_payroll() or not self.salary_slips_submitted:
			return []
		payment_account = frappe.db.get_value("Company", self.company, "custom_default_payroll_payment_account")
		if not payment_account:
			frappe.throw(_("Set Default Payroll Payment Account in Company {0}.").format(self.company))
		return [{"employee": row.employee, "payment_account": payment_account, "cost_center": row.cost_center, "amount": row.amount} for row in self.get_outstanding_payable_rows()]


	@frappe.whitelist()
	def ensure_bank_payment_allocation_defaults(self):
		self.check_permission("write")
		if self.get("custom_bank_payment_allocations"):
			return False
		defaults = self.get_bank_payment_allocation_defaults()
		if not defaults:
			return False
		for allocation in defaults:
			self.append("custom_bank_payment_allocations", allocation)
		self.payment_account = defaults[0]["payment_account"]
		self.save()
		return True

	@frappe.whitelist()
	def get_bank_entry_name(self):
		self.check_permission("read")
		result = frappe.db.sql(
			"""
			select je.name
			from `tabJournal Entry` je
			inner join `tabJournal Entry Account` jea on jea.parent = je.name
			where je.voucher_type = 'Bank Entry'
				and je.docstatus < 2
				and jea.reference_type = 'Payroll Entry'
				and jea.reference_name = %s
			order by je.creation desc
			limit 1
			""",
			self.name,
		)
		return result[0][0] if result else None

	def set_accounting_entries_for_bank_entry(self, je_payment_amount, user_remark):
		rows = self.get("custom_bank_payment_allocations") or []
		if not self._is_managed_payroll() or not rows:
			return super().set_accounting_entries_for_bank_entry(je_payment_amount, user_remark)
		draft_entry = frappe.db.sql("""select j.name from `tabJournal Entry` j join `tabJournal Entry Account` a on a.parent=j.name where j.docstatus=0 and j.voucher_type='Bank Entry' and a.reference_type='Payroll Entry' and a.reference_name=%s limit 1""", self.name)
		if draft_entry:
			frappe.throw(_("Submit or cancel the existing draft Bank Entry {0} before creating another payment.").format(draft_entry[0][0]))
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
		company_currency = erpnext.get_company_currency(self.company)
		dimensions = get_accounting_dimensions() or []
		currencies, credits, debits = [], {}, {}
		outstanding = {(r.employee, r.cost_center): r.amount for r in self.get_outstanding_payable_rows(precision)}
		for row in rows:
			account = frappe.db.get_value("Account", row.payment_account, ["company", "account_type", "is_group", "disabled"], as_dict=True)
			if not account or account.company != self.company or account.is_group or account.disabled or account.account_type not in ("Bank", "Cash"):
				frappe.throw(_("Row {0}: select an enabled Bank or Cash ledger belonging to {1}.").format(row.idx, self.company))
			if frappe.db.get_value("Employee", row.employee, "company") != self.company:
				frappe.throw(_("Row {0}: employee must belong to {1}.").format(row.idx, self.company))
			if frappe.db.get_value("Cost Center", row.cost_center, "company") != self.company:
				frappe.throw(_("Row {0}: cost center must belong to {1}.").format(row.idx, self.company))
			if flt(row.amount) <= 0:
				frappe.throw(_("Row {0}: amount must be greater than zero.").format(row.idx))
			key = (row.employee, row.cost_center)
			debits[key] = debits.get(key, 0) + flt(row.amount)
			credits[(row.payment_account, row.cost_center)] = credits.get((row.payment_account, row.cost_center), 0) + flt(row.amount)
		for key, amount in debits.items():
			if amount > outstanding.get(key, 0) + 0.01:
				frappe.throw(_("Payment for employee {0} and cost center {1} exceeds the outstanding payroll payable.").format(*key))
		accounts = []
		for (account, cost_center), amount in sorted(credits.items()):
			rate, converted = self.get_amount_and_exchange_rate_for_journal_entry(account, amount, company_currency, currencies)
			accounts.append(self.update_accounting_dimensions({"account": account, "credit_in_account_currency": flt(converted, precision), "exchange_rate": flt(rate), "cost_center": cost_center}, dimensions))
		for (employee, cost_center), amount in sorted(debits.items()):
			rate, converted = self.get_amount_and_exchange_rate_for_journal_entry(self.payroll_payable_account, amount, company_currency, currencies)
			accounts.append(self.update_accounting_dimensions({"account": self.payroll_payable_account, "debit_in_account_currency": flt(converted, precision), "exchange_rate": flt(rate), "reference_type": self.doctype, "reference_name": self.name, "party_type": "Employee", "party": employee, "cost_center": cost_center}, dimensions))
		self.make_journal_entry(accounts, currencies, voucher_type="Bank Entry", user_remark=_("Payroll payment from {0} to {1}").format(self.start_date, self.end_date))
		self.set("custom_bank_payment_allocations", [])
		self.flags.ignore_validate_update_after_submit = True
		self.save(ignore_permissions=True)


	def _get_managed_payable_rows(self, precision):
		rows = []
		deductions = {}
		for deduction in self.get("custom_manual_deductions") or []:
			key = (deduction.employee, deduction.source_cost_center)
			deductions[key] = deductions.get(key, 0) + flt(deduction.amount)
		slips = frappe.get_all("Salary Slip", filters={"payroll_entry": self.name, "docstatus": 1}, fields=["employee", "net_pay"], order_by="employee")
		for slip in slips:
			amounts = {}
			for component in PROFILE_COMPONENTS:
				for allocation in self._profile_allocations(slip.employee, component):
					amounts[allocation.cost_center] = amounts.get(allocation.cost_center, 0) + flt(allocation.amount)
			for (employee, cost_center), amount in deductions.items():
				if employee == slip.employee:
					amounts[cost_center] = amounts.get(cost_center, 0) - amount
			unallocated_deduction = max(sum(amounts.values()) - flt(slip.net_pay), 0)
			positive_total = sum(max(amount, 0) for amount in amounts.values())
			if unallocated_deduction and positive_total:
				for cost_center in list(amounts):
					amounts[cost_center] -= unallocated_deduction * max(amounts[cost_center], 0) / positive_total
			if not amounts:
				amounts = {self.cost_center: flt(slip.net_pay)}
			if abs(sum(amounts.values()) - flt(slip.net_pay)) > 0.01:
				frappe.throw(_("Deduction allocation does not reconcile with net salary for employee {0}.").format(slip.employee))
			for cost_center, amount in sorted(amounts.items()):
				if amount < -0.01:
					frappe.throw(_("Deductions exceed salary allocated to cost center {0} for employee {1}.").format(cost_center, slip.employee))
				if amount > 0.01:
					rows.append(frappe._dict(employee=slip.employee, cost_center=cost_center, amount=round(flt(amount), int(precision))))
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
		result = super().make_journal_entry(expanded, *args, **kwargs)
		run = self.get("custom_payment_payroll_run") or self.get("custom_multi_company_payroll_run")
		if run:
			journal = frappe.db.sql("""select j.name from `tabJournal Entry` j join `tabJournal Entry Account` a on a.parent=j.name where j.docstatus<2 and a.reference_type='Payroll Entry' and a.reference_name=%s order by j.creation desc limit 1""", self.name)
			if journal:
				frappe.db.set_value("Journal Entry", journal[0][0], "custom_multi_company_payroll_run", run, update_modified=False)
		return result

	def email_salary_slip(self, submitted_ss):
		"""Custom multi-company payroll keeps slips in-app and never emails them."""
		if self._is_managed_payroll() or self.flags.get("suppress_salary_slip_email"):
			return
		return super().email_salary_slip(submitted_ss)

	def get_salary_component_total(self, component_type=None, employee_wise_accounting_enabled=False):
		if component_type not in ("earnings", "deductions") or not self._is_managed_payroll():
			return super().get_salary_component_total(component_type, employee_wise_accounting_enabled)
		items = self.get_salary_components(component_type)
		if not items:
			return None
		account_dict = {}
		manual_rows = self.get("custom_manual_deductions") or []
		for item in items:
			allocations = self._profile_allocations(item.employee, item.salary_component) if component_type == "earnings" else [row for row in manual_rows if row.employee == item.employee and row.salary_component == item.salary_component]
			employee_advance = self.get_advance_deduction(component_type, item)
			if employee_advance:
				for cost_center, percentage in self.get_payroll_cost_centers_for_employee(item.employee, item.salary_structure).items():
					amount = flt(item.amount) * percentage / 100
					self.add_advance_deduction_entry(item, amount, cost_center, employee_advance)
					if employee_wise_accounting_enabled:
						self.set_employee_based_payroll_payable_entries(component_type, item.employee, amount)
				continue
			if allocations:
				allocation_total = sum(flt(row.amount) for row in allocations)
				for allocation in allocations:
					amount = flt(item.amount) * flt(allocation.amount) / allocation_total
					account = allocation.account if component_type == "earnings" else allocation.source_account
					cost_center = allocation.cost_center if component_type == "earnings" else allocation.source_cost_center
					key = (account, cost_center)
					account_dict[key] = account_dict.get(key, 0) + amount
					if component_type == "earnings":
						party_key = (account, cost_center, item.employee)
						self._profile_party_amounts = getattr(self, "_profile_party_amounts", {})
						self._profile_party_amounts[party_key] = self._profile_party_amounts.get(party_key, 0) + amount
					if employee_wise_accounting_enabled:
						self.set_employee_based_payroll_payable_entries(component_type, item.employee, amount)
				continue
			account = self.get_salary_component_account(item.salary_component)
			for cost_center, percentage in self.get_payroll_cost_centers_for_employee(item.employee, item.salary_structure).items():
				amount = flt(item.amount) * percentage / 100
				account_dict[(account, cost_center)] = account_dict.get((account, cost_center), 0) + amount
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
