from calendar import monthrange

import frappe

from accounting_custom.accounting.consolidated_payslip import sync_consolidated_payslip
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from accounting_custom.accounting.employee_profile import get_payroll_employee


class MultiCompanyPayrollRun(Document):
	def validate(self):
		self._set_month_period()
		if self.start_date and self.end_date and getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("Start Date cannot be after End Date."))
		self._map_and_validate_deductions()
		self._refresh_employee_totals()
		if self.docstatus == 0:
			self._refresh_company_totals()
		self._validate_company_rows(require_accounts=self.docstatus == 1)
		if self.docstatus == 1:
			self._validate_payroll_prerequisites()

	def _set_month_period(self):
		months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
		if not self.payroll_month and self.start_date:
			self.payroll_month = months[getdate(self.start_date).month - 1]
		if not self.payroll_year and self.start_date:
			self.payroll_year = getdate(self.start_date).year
		if self.payroll_month not in months or not int(self.payroll_year or 0):
			frappe.throw(_("Select a valid Payroll Month and Payroll Year."))
		month = months.index(self.payroll_month) + 1
		year = int(self.payroll_year)
		self.start_date = f"{year:04d}-{month:02d}-01"
		self.end_date = f"{year:04d}-{month:02d}-{monthrange(year, month)[1]:02d}"
		self.payroll_frequency = "Monthly"

	def before_submit(self):
		self._validate_payroll_prerequisites()
		if not self.employees or not self.allocation_summary:
			frappe.throw(_("Get Employees before submitting payroll."))
		self.status = "Processing"
		self.approval_status = "Direct Accounts Manager Approval"
		self._clear_missing_payroll_entry_links()
		self._create_payroll_entries()
		queued = False
		for company_row in self.companies:
			queued = self._process_company(company_row) or queued
		if queued:
			self.status = "Processing"
			frappe.msgprint(_("Large payroll processing has been queued and will complete in the background."), indicator="blue")
			return
		self._complete_processing()

	def on_submit(self):
		if self.status == "Processing":
			frappe.enqueue(
				complete_queued_payroll_run,
				queue="long",
				timeout=3000,
				enqueue_after_commit=True,
				payroll_run=self.name,
			)

	def _complete_processing(self):
		self._configure_payment_plans()
		self._refresh_generated_documents()
		self.status = "Completed"
		frappe.msgprint(
			_("Salary Slips submitted for period from {0} to {1}").format(
				self.start_date, self.end_date
			)
		)

	def on_cancel(self):
		processed = set()
		for row in reversed(self.companies):
			for entry_name in reversed(self._company_entry_names(row.company, row)):
				if entry_name in processed or not frappe.db.exists("Payroll Entry", entry_name):
					continue
				processed.add(entry_name)
				entry = frappe.get_doc("Payroll Entry", entry_name)
				if entry.get("custom_multi_company_payroll_run") != self.name:
					linked_payment = frappe.db.exists("Journal Entry", {"custom_multi_company_payroll_run": self.name, "docstatus": ["<", 2]})
					if linked_payment:
						frappe.throw(_("Cancel or delete Bank Entry {0} before cancelling this payroll release.").format(linked_payment))
					if entry.get("custom_payment_payroll_run") == self.name:
						entry.set("custom_bank_payment_allocations", [])
						entry.custom_payment_payroll_run = None
						entry.flags.ignore_validate_update_after_submit = True
						entry.save(ignore_permissions=True)
					continue
				if entry.docstatus == 1:
					entry.cancel()
				elif entry.docstatus == 0:
					for slip in entry.get_linked_salary_slips():
						frappe.delete_doc("Salary Slip", slip.name, ignore_permissions=True)
		self.db_set("status", "Cancelled", update_modified=False)

	def _clear_missing_payroll_entry_links(self):
		linked_names = {
			name for name in [
				*[row.payroll_entry for row in self.companies if row.payroll_entry],
				*[row.source_payroll_entry for row in self.employees if row.source_payroll_entry],
			] if name
		}
		existing = set(frappe.get_all("Payroll Entry", filters={"name": ["in", list(linked_names)]}, pluck="name")) if linked_names else set()
		for row in self.companies:
			if row.payroll_entry and row.payroll_entry not in existing:
				row.payroll_entry = None
				row.payroll_entry_count = 0
				row.status = "Ready"
		for row in self.employees:
			if row.source_payroll_entry and row.source_payroll_entry not in existing:
				row.source_payroll_entry = None
				row.salary_slip = None
				row.status = "Ready"

	def _company_entry_names(self, company, company_row=None):
		entries = {row.source_payroll_entry for row in self.employees if row.company == company and row.source_payroll_entry}
		if company_row and company_row.payroll_entry:
			entries.add(company_row.payroll_entry)
		return sorted(entries)

	def _validate_company_rows(self, require_accounts=False):
		for row in self.companies:
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
			valid_source = any(
				allocation.employee == row.employee and allocation.company == row.company
				and allocation.component == row.source_component and allocation.account == row.source_account
				and allocation.cost_center == row.source_cost_center
				for allocation in self.allocation_summary
			)
			if not valid_source:
				frappe.throw(_("Deduction row {0}: source component, account, and cost center must match the employee salary allocation.").format(row.idx))

	def _refresh_employee_totals(self):
		deductions = {}
		for row in self.manual_deductions:
			deductions[row.payroll_employee] = deductions.get(row.payroll_employee, 0) + flt(row.amount)
		for row in self.employees:
			previous_available = max(flt(row.net_salary) - flt(row.previously_paid), 0)
			was_full_payment = abs(flt(row.pay_this_run) - previous_available) <= 0.01
			scheduled = 0 if row.source_payroll_entry else self._scheduled_advance_deductions(row.payroll_employee)
			row.deductions = 0 if row.source_payroll_entry else deductions.get(row.payroll_employee, 0) + scheduled
			row.net_salary = flt(row.gross_salary) - flt(row.deductions)
			available = max(flt(row.net_salary) - flt(row.previously_paid), 0)
			if flt(row.pay_this_run) < 0:
				frappe.throw(_("Pay This Run for {0} - {1} cannot be negative.").format(row.employee_name, row.company))
			if was_full_payment or flt(row.pay_this_run) > available:
				row.pay_this_run = available
			row.deferred_amount = available - flt(row.pay_this_run)

	def _refresh_company_totals(self):
		preserved_fields = (
			"company", "payroll_payable_account", "currency", "payroll_entry",
			"payroll_entry_count", "salary_slip_count", "journal_entry", "status", "error_message",
		)
		existing = {
			row.company: {fieldname: row.get(fieldname) for fieldname in preserved_fields}
			for row in self.companies
		}
		company_order = []
		for row in self.employees:
			if row.company and row.company not in company_order:
				company_order.append(row.company)
		self.set("companies", [])
		for company in company_order:
			rows = [row for row in self.employees if row.company == company]
			values = existing.get(company, {})
			if not values:
				payable, currency = frappe.db.get_value(
					"Company", company, ["default_payroll_payable_account", "default_currency"]
				) or (None, None)
				values = {"company": company, "payroll_payable_account": payable, "currency": currency, "status": "Ready"}
			values["employee_count"] = len({row.payroll_employee for row in rows})
			values["gross_salary"] = sum(flt(row.pay_this_run) for row in rows)
			self.append("companies", values)

	def _scheduled_advance_deductions(self, employee):
		return flt(frappe.db.sql("""select sum(amount) from `tabAdditional Salary` where employee=%s and company in (select company from `tabEmployee` where name=%s) and docstatus=1 and disabled=0 and ref_doctype='Employee Advance' and ((is_recurring=1 and from_date<=%s and to_date>=%s) or (is_recurring=0 and payroll_date between %s and %s))""", (employee, employee, self.end_date, self.start_date, self.start_date, self.end_date))[0][0])


	@frappe.whitelist()
	def get_employees(self):
		self.check_permission("write")
		if self.docstatus:
			frappe.throw(_("Employees can only be loaded in Draft."))
		self._set_month_period()
		from accounting_custom.accounting.salary_advance import ensure_paid_installment_schedules
		ensure_paid_installment_schedules()
		if any(row.payroll_entry for row in self.companies):
			frappe.throw(_("Payroll Entries already exist. Amend or create a new run."))
		self.set("companies", [])
		self.set("employees", [])
		self.set("allocation_summary", [])
		groups, people = {}, {}
		for profile in frappe.get_all("Employee Salary Profile", pluck="name"):
			# Monthly payroll uses the salary that is effective on the first day of
			# the period. A later revision naturally applies from the next month.
			revs = frappe.db.sql("""
				select name, employee, employee_name, effective_from
				from `tabEmployee Salary Revision`
				where salary_profile=%s and effective_from<=%s
				and (effective_to is null or effective_to>=%s)
				order by effective_from desc, revision_number desc limit 1
			""", (profile, self.start_date, self.start_date), as_dict=True)
			if not revs:
				continue
			rev = revs[0]
			for alloc in frappe.get_all("Employee Salary Revision Allocation", filters={"parent": rev.name, "parenttype": "Employee Salary Revision"}, fields=["component", "company", "account", "cost_center", "amount"], order_by="idx"):
				payroll_employee = get_payroll_employee(rev.employee, alloc.company)
				if not payroll_employee:
					frappe.throw(_("No payroll employee exists for {0} in {1}.").format(rev.employee_name or rev.employee, alloc.company))
				slip = self._existing_salary_slip(payroll_employee)
				entry = slip.payroll_entry if slip else ""
				key = (rev.employee, alloc.company, payroll_employee, entry)
				person = people.setdefault(key, {"name": rev.employee_name, "gross": 0, "slip": slip})
				person["gross"] += flt(alloc.amount)
				self.append("allocation_summary", {"employee": rev.employee, "employee_name": rev.employee_name, "company": alloc.company, "payroll_employee": payroll_employee, "component": alloc.component, "account": alloc.account, "cost_center": alloc.cost_center, "amount": alloc.amount, "salary_revision": rev.name})
		for (employee, company, payroll_employee, entry), data in sorted(people.items()):
			paid = self._paid_amount(entry, payroll_employee)
			net = flt(data["slip"].net_pay) if data["slip"] else data["gross"]
			outstanding = max(net - paid, 0)
			if entry and outstanding <= 0.01:
				continue
			scheduled = 0 if entry else self._scheduled_advance_deductions(payroll_employee)
			net_after_deductions = net if entry else net - scheduled
			outstanding = max(net_after_deductions - paid, 0)
			self.append("employees", {"employee": employee, "employee_name": data["name"], "company": company, "payroll_employee": payroll_employee, "gross_salary": net, "deductions": scheduled, "previously_paid": paid, "pay_this_run": outstanding, "deferred_amount": 0, "net_salary": net_after_deductions, "source_payroll_entry": entry or None, "salary_slip": data["slip"].name if data["slip"] else None, "status": "Outstanding Payment" if entry else "Ready"})
			g = groups.setdefault(company, {"employees": set(), "amount": 0, "entries": set(), "needs_new_entry": False})
			g["employees"].add(payroll_employee)
			g["amount"] += outstanding
			if entry: g["entries"].add(entry)
			else: g["needs_new_entry"] = True
		if not self.employees:
			frappe.throw(_("No unpaid employees were found for this payroll month."))
		for company, data in sorted(groups.items()):
			payable, currency = frappe.db.get_value("Company", company, ["default_payroll_payable_account", "default_currency"]) or (None, None)
			entry = next(iter(data["entries"])) if len(data["entries"]) == 1 and not data["needs_new_entry"] else None
			status = "Outstanding Payment" if data["entries"] and not data["needs_new_entry"] else "Ready"
			self.append("companies", {"company": company, "payroll_payable_account": payable, "currency": currency, "employee_count": len(data["employees"]), "gross_salary": data["amount"], "payroll_entry": entry, "payroll_entry_count": len(data["entries"]), "status": status})
		self.status = "Employees Loaded"
		self.save()
		return {"companies": len(self.companies), "employees": len(self.employees)}

	def _existing_salary_slip(self, employee):
		name = frappe.db.get_value("Salary Slip", {"employee": employee, "start_date": self.start_date, "end_date": self.end_date, "docstatus": 1}, "name")
		return frappe.get_doc("Salary Slip", name) if name else None

	def _paid_amount(self, payroll_entry, employee):
		if not payroll_entry:
			return 0
		return flt(frappe.db.sql("""select sum(a.debit_in_account_currency) from `tabJournal Entry Account` a join `tabJournal Entry` j on j.name=a.parent where j.docstatus=1 and j.voucher_type='Bank Entry' and a.reference_type='Payroll Entry' and a.reference_name=%s and a.party_type='Employee' and a.party=%s""", (payroll_entry, employee))[0][0])


	def _create_payroll_entries(self):
		self._validate_company_rows(require_accounts=True)
		for company_row in self.companies:
			if company_row.payroll_entry and frappe.db.exists("Payroll Entry", company_row.payroll_entry):
				continue
			employees = sorted({r.payroll_employee for r in self.employees if r.company == company_row.company and not r.source_payroll_entry})
			if not employees:
				continue
			allocations = [r for r in self.allocation_summary if r.company == company_row.company and r.payroll_employee in employees]
			entry=frappe.get_doc({"doctype":"Payroll Entry","custom_multi_company_payroll_run":self.name,"posting_date":self.posting_date,"company":company_row.company,"currency":company_row.currency,"exchange_rate":1,"payroll_payable_account":company_row.payroll_payable_account,"payroll_frequency":self.payroll_frequency,"start_date":self.start_date,"end_date":self.end_date,"cost_center":allocations[0].cost_center,"employees":[{"employee":e} for e in employees]})
			for deduction in self.manual_deductions:
				if deduction.company==company_row.company: entry.append("custom_manual_deductions", {"employee":deduction.payroll_employee,"source_component":deduction.source_component,"source_account":deduction.source_account,"source_cost_center":deduction.source_cost_center,"salary_component":deduction.salary_component,"amount":deduction.amount,"note":deduction.note})
			entry.insert()
			company_row.payroll_entry = entry.name
			company_row.status = "Created"
			for employee_row in self.employees:
				if employee_row.company == company_row.company and not employee_row.source_payroll_entry:
					employee_row.source_payroll_entry = entry.name

	def _process_company(self, row):
		if not row.payroll_entry:
			row.status = "Payment Release" if self._company_entry_names(row.company, row) else "Deferred"
			return
		entry=frappe.get_doc("Payroll Entry", row.payroll_entry)
		if len(entry.employees) > 30:
			# Do not submit before the parent transaction commits. HRMS queues slip
			# creation from Payroll Entry.on_submit and that worker must be able to
			# read this newly-created Payroll Entry from the database.
			row.status = "Queued"
			return True
		if entry.docstatus==0: entry.submit()
		if not entry.salary_slips_submitted:
			entry.flags.suppress_salary_slip_email = True
			message_count = len(frappe.local.message_log)
			entry.submit_salary_slips()
			success_message = _("Salary Slips submitted for period from {0} to {1}").format(
				entry.start_date, entry.end_date
			)
			frappe.local.message_log = frappe.local.message_log[:message_count] + [
				message for message in frappe.local.message_log[message_count:]
				if message.get("message") != success_message
			]
			entry.reload()
			if not entry.salary_slips_submitted:
				frappe.throw(_("Salary Slip submission failed for company {0}. Open Payroll Entry {1} for details.").format(row.company, entry.name))
		row.status="Completed"
		return False


	def _configure_payment_plans(self):
		for company_row in self.companies:
			payment_account = frappe.db.get_value("Company", company_row.company, "custom_default_payroll_payment_account")
			if not payment_account:
				frappe.throw(_("Set Default Payroll Payment Account in Company {0}.").format(company_row.company))
			for entry_name in self._company_entry_names(company_row.company, company_row):
				entry = frappe.get_doc("Payroll Entry", entry_name)
				plans = {r.payroll_employee: flt(r.pay_this_run) for r in self.employees if r.source_payroll_entry == entry.name}
				entry.set("custom_bank_payment_allocations", [])
				by_employee = {}
				for payable in entry.get_outstanding_payable_rows():
					by_employee.setdefault(payable.employee, []).append(payable)
				for employee, target in plans.items():
					rows = by_employee.get(employee, [])
					available = sum(flt(row.amount) for row in rows)
					if target > available + 0.01:
						frappe.throw(_("Pay This Run for employee {0} exceeds the outstanding payable.").format(employee))
					remaining = target
					for index, payable in enumerate(rows):
						amount = remaining if index == len(rows) - 1 else min(flt(payable.amount), flt(target) * flt(payable.amount) / available) if available else 0
						remaining -= amount
						if amount > 0.01:
							entry.append("custom_bank_payment_allocations", {"employee": employee, "payment_account": payment_account, "cost_center": payable.cost_center, "amount": amount})
				entry.payment_account = payment_account
				entry.custom_payment_payroll_run = self.name
				entry.flags.ignore_validate_update_after_submit = True
				entry.save(ignore_permissions=True)

	def _refresh_generated_documents(self):
		for company_row in self.companies:
			entry_names = self._company_entry_names(company_row.company, company_row)
			company_row.payroll_entry_count = len(entry_names)
			all_slips, journals = [], []
			for entry_name in entry_names:
				all_slips.extend(frappe.get_all("Salary Slip", filters={"payroll_entry": entry_name, "docstatus": 1}, fields=["name", "employee", "net_pay"]))
				journals.extend(frappe.get_all("Journal Entry Account", filters={"reference_type": "Payroll Entry", "reference_name": entry_name, "docstatus": 1}, pluck="parent", distinct=True))
			company_row.salary_slip_count = len(all_slips)
			company_row.journal_entry = journals[0] if len(set(journals)) == 1 else None
			if len(entry_names) > 1:
				company_row.payroll_entry = None
			company_row.status = _("Completed ({0} Payroll Entries)").format(len(entry_names)) if len(entry_names) > 1 else "Completed"
			by_employee = {slip.employee: slip for slip in all_slips}
			for employee_row in self.employees:
				if employee_row.company != company_row.company: continue
				slip = by_employee.get(employee_row.payroll_employee)
				employee_row.salary_slip = slip.name if slip else employee_row.salary_slip
				employee_row.net_salary = slip.net_pay if slip else employee_row.net_salary
				employee_row.status = "Payment Ready" if employee_row.pay_this_run else "Deferred"
		for employee in {row.employee for row in self.employees}:
			sync_consolidated_payslip(employee, self.start_date, self.end_date)


def complete_queued_payroll_run(payroll_run):
	"""Complete a large payroll safely in a long-running background worker."""
	from hrms.payroll.doctype.payroll_entry.payroll_entry import (
		create_salary_slips_for_employees,
		submit_salary_slips_for_employees,
	)

	run = frappe.get_doc("Multi Company Payroll Run", payroll_run)
	if run.docstatus != 1 or run.status == "Completed":
		return
	try:
		for company_row in run.companies:
			if company_row.status != "Queued" or not company_row.payroll_entry:
				continue
			entry = frappe.get_doc("Payroll Entry", company_row.payroll_entry)
			if entry.docstatus == 0:
				# This function already owns a long worker. Avoid a second creation job.
				frappe.flags.accounting_custom_sync_payroll = True
				try:
					entry.submit()
				finally:
					frappe.flags.accounting_custom_sync_payroll = False
				entry.reload()
			if not entry.salary_slips_created:
				args = frappe._dict({
					"salary_slip_based_on_timesheet": entry.salary_slip_based_on_timesheet,
					"payroll_frequency": entry.payroll_frequency,
					"start_date": entry.start_date, "end_date": entry.end_date,
					"company": entry.company, "posting_date": entry.posting_date,
					"deduct_tax_for_unclaimed_employee_benefits": entry.deduct_tax_for_unclaimed_employee_benefits,
					"deduct_tax_for_unsubmitted_tax_exemption_proof": entry.deduct_tax_for_unsubmitted_tax_exemption_proof,
					"payroll_entry": entry.name, "exchange_rate": entry.exchange_rate,
					"currency": entry.currency,
				})
				create_salary_slips_for_employees([row.employee for row in entry.employees], args, publish_progress=False)
				entry.reload()
			if not entry.salary_slips_submitted:
				draft_slips = entry.get_sal_slip_list(ss_status=0)
				if draft_slips:
					submit_salary_slips_for_employees(entry, draft_slips, publish_progress=False)
				entry.reload()
			if not entry.salary_slips_submitted:
				frappe.throw(_("Salary Slip submission failed for company {0}.").format(company_row.company))
			company_row.status = "Completed"
		run._complete_processing()
		run.flags.ignore_validate_update_after_submit = True
		run.save(ignore_permissions=True)
	except Exception:
		frappe.db.set_value("Multi Company Payroll Run", payroll_run, "status", "Failed", update_modified=False)
		frappe.log_error(title=f"Large payroll processing failed: {payroll_run}")
		raise
