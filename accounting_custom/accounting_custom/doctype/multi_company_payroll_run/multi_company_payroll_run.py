import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from accounting_custom.accounting.employee_profile import get_payroll_employee


class MultiCompanyPayrollRun(Document):
	def validate(self):
		if self.start_date and self.end_date and getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("Start Date cannot be after End Date."))
		self._validate_company_rows()

	def _validate_company_rows(self, require_accounts=False):
		seen = set()
		for row in self.companies:
			if row.company in seen:
				frappe.throw(_("Company {0} is duplicated.").format(row.company))
			seen.add(row.company)
			if not row.payroll_payable_account:
				if require_accounts:
					frappe.throw(_("Select a Payroll Payable Account for company {0}.").format(row.company))
				continue
			account = frappe.db.get_value("Account", row.payroll_payable_account, ["company", "is_group", "disabled", "account_type"], as_dict=True)
			if not account or account.company != row.company or account.is_group or account.disabled:
				frappe.throw(_("Select an enabled ledger payroll payable account belonging to {0}.").format(row.company))
			if account.account_type:
				frappe.throw(_("Payroll payable account {0} must not have an Account Type.").format(row.payroll_payable_account))

	@frappe.whitelist()
	def get_employees(self):
		self.check_permission("write")
		if not self.start_date or not self.end_date:
			frappe.throw(_("Enter Start Date and End Date first."))
		if any(row.payroll_entry for row in self.companies):
			frappe.throw(_("Payroll Entries already exist. Create a new run to reload employees."))

		self.set("companies", [])
		self.set("allocation_summary", [])
		profiles = frappe.get_all("Employee Salary Profile", fields=["name", "employee"])
		company_data = {}
		for profile in profiles:
			revision = frappe.get_all(
				"Employee Salary Revision",
				filters={"salary_profile": profile.name, "effective_from": ["<=", self.end_date]},
				fields=["name", "employee", "employee_name", "effective_from"],
				order_by="effective_from desc, revision_number desc", limit=1,
			)
			if not revision:
				continue
			revision = revision[0]
			if getdate(revision.effective_from) > getdate(self.start_date):
				frappe.throw(_("Salary revision {0} for {1} starts during this payroll period. Split the payroll period at {2}.").format(revision.name, revision.employee_name or revision.employee, revision.effective_from))
			allocations = frappe.get_all(
				"Employee Salary Revision Allocation",
				filters={"parent": revision.name, "parenttype": "Employee Salary Revision"},
				fields=["component", "company", "account", "cost_center", "amount"], order_by="idx asc",
			)
			for allocation in allocations:
				payroll_employee = get_payroll_employee(revision.employee, allocation.company)
				if not payroll_employee:
					frappe.throw(_("No payroll employee exists for {0} in {1}.").format(revision.employee_name or revision.employee, allocation.company))
				self.append("allocation_summary", {
					"employee": revision.employee, "employee_name": revision.employee_name,
					"company": allocation.company, "payroll_employee": payroll_employee,
					"component": allocation.component, "account": allocation.account,
					"cost_center": allocation.cost_center, "amount": allocation.amount,
					"salary_revision": revision.name,
				})
				data = company_data.setdefault(allocation.company, {"employees": set(), "gross": 0})
				data["employees"].add(payroll_employee)
				data["gross"] += flt(allocation.amount)

		for company in sorted(company_data):
			payable, currency = frappe.db.get_value("Company", company, ["default_payroll_payable_account", "default_currency"]) or (None, None)
			data = company_data[company]
			self.append("companies", {
				"company": company, "payroll_payable_account": payable, "currency": currency,
				"employee_count": len(data["employees"]), "gross_salary": data["gross"], "status": "Ready",
			})
		if not self.allocation_summary:
			frappe.throw(_("No effective employee salary allocations were found for this period."))
		self.status = "Employees Loaded"
		self.save()
		return {"companies": len(self.companies), "employees": len({row.payroll_employee for row in self.allocation_summary}), "allocations": len(self.allocation_summary)}

	@frappe.whitelist()
	def create_payroll_entries(self):
		self.check_permission("write")
		if not self.companies or not self.allocation_summary:
			frappe.throw(_("Get Employees before creating Payroll Entries."))
		self._validate_company_rows(require_accounts=True)
		for company_row in self.companies:
			if company_row.payroll_entry and frappe.db.exists("Payroll Entry", company_row.payroll_entry):
				continue
			allocations = [row for row in self.allocation_summary if row.company == company_row.company]
			employees = sorted({row.payroll_employee for row in allocations})
			entry = frappe.get_doc({
				"doctype": "Payroll Entry", "posting_date": self.posting_date,
				"company": company_row.company, "currency": company_row.currency,
				"exchange_rate": 1, "payroll_payable_account": company_row.payroll_payable_account,
				"payroll_frequency": self.payroll_frequency, "start_date": self.start_date,
				"end_date": self.end_date, "cost_center": allocations[0].cost_center,
				"employees": [{"employee": employee} for employee in employees],
			})
			entry.insert()
			company_row.payroll_entry = entry.name
			company_row.status = "Payroll Entry Created"
		self.status = "Payroll Entries Created"
		self.save()
		return [row.payroll_entry for row in self.companies]

	@frappe.whitelist()
	def create_salary_slips(self):
		self.check_permission("write")
		if not all(row.payroll_entry for row in self.companies):
			frappe.throw(_("Create Payroll Entries first."))
		for row in self.companies:
			entry = frappe.get_doc("Payroll Entry", row.payroll_entry)
			entry.create_salary_slips()
			row.salary_slip_count = frappe.db.count("Salary Slip", {"payroll_entry": entry.name})
			row.status = "Salary Slips Created"
		self.status = "Salary Slips Created"
		self.save()
		return sum(row.salary_slip_count for row in self.companies)
