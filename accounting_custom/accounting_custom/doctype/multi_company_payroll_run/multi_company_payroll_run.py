import frappe

from accounting_custom.accounting.consolidated_payslip import sync_consolidated_payslip
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from accounting_custom.accounting.employee_profile import get_payroll_employee


class MultiCompanyPayrollRun(Document):
	def validate(self):
		if self.start_date and self.end_date and getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("Start Date cannot be after End Date."))
		self._map_and_validate_deductions()
		self._refresh_employee_totals()
		self._validate_company_rows(require_accounts=self.docstatus == 1)
		if self.docstatus == 1:
			self._validate_payroll_prerequisites()

	def before_submit(self):
		self._validate_payroll_prerequisites()
		if not self.employees or not self.allocation_summary:
			frappe.throw(_("Get Employees before submitting payroll."))
		self.status = "Processing"
		self.approval_status = "Direct Accounts Manager Approval"
		self._create_payroll_entries()
		for company_row in self.companies:
			self._process_company(company_row)
		self._refresh_generated_documents()
		self.status = "Completed"

	def on_cancel(self):
		for row in reversed(self.companies):
			if not row.payroll_entry or not frappe.db.exists("Payroll Entry", row.payroll_entry):
				continue
			entry = frappe.get_doc("Payroll Entry", row.payroll_entry)
			if entry.docstatus == 1:
				entry.cancel()
			elif entry.docstatus == 0:
				for slip in entry.get_linked_salary_slips():
					frappe.delete_doc("Salary Slip", slip.name, ignore_permissions=True)
		self.db_set("status", "Cancelled", update_modified=False)

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
			if account.account_type != "Payable":
				frappe.throw(_("Payroll payable account {0} must have Account Type Payable.").format(row.payroll_payable_account))

	def _validate_payroll_prerequisites(self):
		missing_holiday_lists = []
		for row in self.employees:
			holiday_list = frappe.db.get_value("Employee", row.payroll_employee, "holiday_list") or frappe.db.get_value("Company", row.company, "default_holiday_list")
			if not holiday_list:
				missing_holiday_lists.append(f"{row.employee_name} — {row.company}")
		if missing_holiday_lists:
			frappe.throw(_("Set a Holiday List on the master Employee or Default Holiday List on these companies before submitting payroll: {0}").format(", ".join(missing_holiday_lists)))

	def _map_and_validate_deductions(self):
		valid = {(row.employee, row.company): row.payroll_employee for row in self.employees}
		for row in self.manual_deductions:
			row.payroll_employee = valid.get((row.employee, row.company))
			if not row.payroll_employee:
				frappe.throw(_("Deduction row {0}: employee is not in payroll for company {1}.").format(row.idx, row.company))
			if frappe.db.get_value("Salary Component", row.salary_component, "type") != "Deduction":
				frappe.throw(_("Deduction row {0}: select a Deduction salary component.").format(row.idx))
			if flt(row.amount) <= 0:
				frappe.throw(_("Deduction row {0}: amount must be greater than zero.").format(row.idx))

	def _refresh_employee_totals(self):
		deductions = {}
		for row in self.manual_deductions:
			deductions[row.payroll_employee] = deductions.get(row.payroll_employee, 0) + flt(row.amount)
		for row in self.employees:
			row.deductions = deductions.get(row.payroll_employee, 0)
			row.net_salary = flt(row.gross_salary) - flt(row.deductions)

	@frappe.whitelist()
	def get_employees(self):
		self.check_permission("write")
		if self.docstatus:
			frappe.throw(_("Employees can only be loaded in Draft."))
		if any(row.payroll_entry for row in self.companies):
			frappe.throw(_("Payroll Entries already exist. Amend or create a new run."))
		self.set("companies", []); self.set("employees", []); self.set("allocation_summary", [])
		company_data, employee_data = {}, {}
		for profile in frappe.get_all("Employee Salary Profile", fields=["name"]):
			revisions = frappe.get_all("Employee Salary Revision", filters={"salary_profile": profile.name, "effective_from": ["<=", self.end_date]}, fields=["name", "employee", "employee_name", "effective_from"], order_by="effective_from desc, revision_number desc", limit=1)
			if not revisions: continue
			revision = revisions[0]
			if getdate(revision.effective_from) > getdate(self.start_date):
				frappe.throw(_("Salary revision {0} starts during this payroll period. Split the period at {1}.").format(revision.name, revision.effective_from))
			for allocation in frappe.get_all("Employee Salary Revision Allocation", filters={"parent": revision.name, "parenttype": "Employee Salary Revision"}, fields=["component", "company", "account", "cost_center", "amount"], order_by="idx asc"):
				payroll_employee = get_payroll_employee(revision.employee, allocation.company)
				if not payroll_employee: frappe.throw(_("No payroll employee exists for {0} in {1}.").format(revision.employee_name or revision.employee, allocation.company))
				self.append("allocation_summary", {"employee":revision.employee,"employee_name":revision.employee_name,"company":allocation.company,"payroll_employee":payroll_employee,"component":allocation.component,"account":allocation.account,"cost_center":allocation.cost_center,"amount":allocation.amount,"salary_revision":revision.name})
				company_data.setdefault(allocation.company, {"employees":set(),"gross":0}); company_data[allocation.company]["employees"].add(payroll_employee); company_data[allocation.company]["gross"] += flt(allocation.amount)
				key=(revision.employee, allocation.company, payroll_employee); employee_data.setdefault(key,{"name":revision.employee_name,"gross":0}); employee_data[key]["gross"] += flt(allocation.amount)
		if not self.allocation_summary: frappe.throw(_("No effective salary allocations were found."))
		for company, data in sorted(company_data.items()):
			payable, currency = frappe.db.get_value("Company", company, ["default_payroll_payable_account","default_currency"]) or (None,None)
			self.append("companies", {"company":company,"payroll_payable_account":payable,"currency":currency,"employee_count":len(data["employees"]),"gross_salary":data["gross"],"status":"Ready"})
		for (employee, company, payroll_employee), data in sorted(employee_data.items()):
			self.append("employees", {"employee":employee,"employee_name":data["name"],"company":company,"payroll_employee":payroll_employee,"gross_salary":data["gross"],"net_salary":data["gross"],"status":"Ready"})
		self.status="Employees Loaded"; self.save(); return {"companies":len(self.companies),"employees":len(self.employees)}

	def _create_payroll_entries(self):
		self._validate_company_rows(require_accounts=True)
		for company_row in self.companies:
			if company_row.payroll_entry and frappe.db.exists("Payroll Entry", company_row.payroll_entry): continue
			allocations=[r for r in self.allocation_summary if r.company==company_row.company]; employees=sorted({r.payroll_employee for r in allocations})
			entry=frappe.get_doc({"doctype":"Payroll Entry","custom_multi_company_payroll_run":self.name,"posting_date":self.posting_date,"company":company_row.company,"currency":company_row.currency,"exchange_rate":1,"payroll_payable_account":company_row.payroll_payable_account,"payroll_frequency":self.payroll_frequency,"start_date":self.start_date,"end_date":self.end_date,"cost_center":allocations[0].cost_center,"employees":[{"employee":e} for e in employees]})
			for deduction in self.manual_deductions:
				if deduction.company==company_row.company: entry.append("custom_manual_deductions", {"employee":deduction.payroll_employee,"salary_component":deduction.salary_component,"amount":deduction.amount,"note":deduction.note})
			entry.insert(); company_row.payroll_entry=entry.name; company_row.status="Created"

	def _process_company(self, row):
		entry=frappe.get_doc("Payroll Entry", row.payroll_entry)
		if len(entry.employees)>30: frappe.throw(_("Company {0} has more than 30 employees. Split the run to ensure synchronous audited processing.").format(row.company))
		if entry.docstatus==0: entry.submit()
		if not entry.salary_slips_submitted:
			entry.flags.suppress_salary_slip_email = True
			entry.submit_salary_slips()
			entry.reload()
			if not entry.salary_slips_submitted:
				frappe.throw(_("Salary Slip submission failed for company {0}. Open Payroll Entry {1} for details.").format(row.company, entry.name))
		row.status="Completed"

	def _refresh_generated_documents(self):
		for company_row in self.companies:
			slips=frappe.get_all("Salary Slip", filters={"payroll_entry":company_row.payroll_entry,"docstatus":1}, fields=["name","employee","net_pay"])
			company_row.salary_slip_count=len(slips)
			journals=frappe.get_all("Journal Entry Account", filters={"reference_type":"Payroll Entry","reference_name":company_row.payroll_entry,"docstatus":1}, pluck="parent", distinct=True)
			company_row.journal_entry=journals[0] if journals else None
			by_employee={s.employee:s for s in slips}
			for employee_row in self.employees:
				if employee_row.company!=company_row.company: continue
				slip=by_employee.get(employee_row.payroll_employee)
				employee_row.salary_slip=slip.name if slip else None; employee_row.net_salary=slip.net_pay if slip else employee_row.net_salary; employee_row.status="Completed" if slip else "Failed"
		for employee in {row.employee for row in self.employees}:
			sync_consolidated_payslip(employee, self.start_date, self.end_date)
