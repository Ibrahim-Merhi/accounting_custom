import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate


COMPONENT_TABLES = {
	"Basic Salary": ("basic_salary", "basic_allocations"),
	"Transportation": ("transportation", "transportation_allocations"),
	"Family Allowance": ("family_allowance", "family_allowance_allocations"),
}


class EmployeeSalaryProfile(Document):
	def validate(self):
		self._validate_access()
		self._validate_dates()
		self._calculate_component_totals()
		self.total_salary = flt(self.basic_salary) + flt(self.transportation) + flt(self.family_allowance)
		allowed_companies = self._get_employee_companies()
		self._validate_company_currencies(allowed_companies)
		for component, (amount_field, table_field) in COMPONENT_TABLES.items():
			self._validate_allocations(
				component, flt(self.get(amount_field)), table_field, allowed_companies
			)
		if self._salary_configuration_changed() and not self.action_date:
			frappe.throw(_("Enter the Date of Action for this salary change."))

	def on_update(self):
		if not self._salary_configuration_changed() or not self.action_date:
			return
		revision = self._create_revision()
		self.db_set({
			"latest_revision": revision.name,
			"last_action_date": self.action_date,
			"action_date": None,
		}, update_modified=False)
		self.action_date = None

	def on_trash(self):
		if frappe.db.exists("Employee Salary Revision", {"salary_profile": self.name}):
			frappe.throw(_("A salary profile with revisions cannot be deleted."))

	def _validate_access(self):
		if frappe.session.user == "Administrator":
			return
		roles = set(frappe.get_roles())
		if "Accounts Manager" not in roles:
			frappe.throw(_("Only Accounts Manager can access employee salary profiles."), frappe.PermissionError)

	def _validate_dates(self):
		latest_effective = frappe.db.get_value(
			"Employee Salary Revision", {"salary_profile": self.name}, "effective_from",
			order_by="revision_number desc",
		)
		if latest_effective and getdate(self.effective_date) <= getdate(latest_effective):
			frappe.throw(_("Start Effective Date must be after the latest salary revision."))

	def _get_employee_companies(self):
		companies = {
			row.company for row in frappe.get_all(
				"Employee Branch Assignment",
				filters={"parent": self.employee, "parenttype": "Employee"},
				fields=["company"],
			) if row.company
		}
		if not companies:
			company = frappe.db.get_value("Employee", self.employee, "company")
			if company:
				companies.add(company)
		return companies

	def _validate_company_currencies(self, companies):
		currencies = {frappe.db.get_value("Company", company, "default_currency") for company in companies}
		currencies.discard(None)
		if len(currencies) > 1:
			frappe.throw(_("All companies in one salary profile must use the same default currency."))

	def _calculate_component_totals(self):
		row_count = 0
		for _component, (amount_field, table_field) in COMPONENT_TABLES.items():
			rows = self.get(table_field) or []
			row_count += len(rows)
			self.set(amount_field, flt(sum(flt(row.amount) for row in rows), 2))
		if not row_count:
			frappe.throw(_("Add at least one salary allocation row in Basic Salary, Transportation, or Family Allowance."))

	def _validate_allocations(self, component, component_amount, table_field, allowed_companies):
		rows = self.get(table_field) or []
		if not rows:
			return
		total_percentage = 0
		seen = set()
		for row in rows:
			if row.company not in allowed_companies:
				frappe.throw(_("Row {0}: Company {1} is not an active employment company for this employee.").format(row.idx, row.company))
			account = frappe.db.get_value("Account", row.account, ["company", "is_group", "disabled"], as_dict=True)
			if not account or account.company != row.company or account.is_group or account.disabled:
				frappe.throw(_("Row {0}: Select an enabled ledger account belonging to {1}.").format(row.idx, row.company))
			cost_center = frappe.db.get_value("Cost Center", row.cost_center, ["company", "is_group", "disabled"], as_dict=True)
			if not cost_center or cost_center.company != row.company or cost_center.is_group or cost_center.disabled:
				frappe.throw(_("Row {0}: Select an enabled cost center belonging to {1}.").format(row.idx, row.company))
			key = (row.company, row.account, row.cost_center)
			if key in seen:
				frappe.throw(_("Row {0}: This company, account, and cost center allocation is duplicated.").format(row.idx))
			seen.add(key)
			if flt(row.amount) <= 0:
				frappe.throw(_("Row {0}: Amount must be greater than zero.").format(row.idx))
			if flt(row.percentage) <= 0 or flt(row.percentage) > 100:
				frappe.throw(_("Row {0}: Percentage must be greater than 0% and no more than 100%.").format(row.idx))
			total_percentage += flt(row.percentage)
		if abs(total_percentage - 100) > 0.001:
			frappe.throw(_("{0} allocation percentages must total exactly 100% (currently {1}%).").format(component, total_percentage))
		if component_amount <= 0:
			frappe.throw(_("{0} total must be greater than zero.").format(component))

	def _salary_configuration_changed(self):
		before = self.get_doc_before_save()
		if not before:
			return True
		fields = ("effective_date", "basic_salary", "transportation", "family_allowance")
		if any(self.get(field) != before.get(field) for field in fields):
			return True
		for _component, (_amount_field, table_field) in COMPONENT_TABLES.items():
			current = [self._allocation_tuple(row) for row in self.get(table_field)]
			previous = [self._allocation_tuple(row) for row in before.get(table_field)]
			if current != previous:
				return True
		return False

	@staticmethod
	def _allocation_tuple(row):
		return (row.company, row.account, row.cost_center, flt(row.percentage), flt(row.amount))

	def _create_revision(self):
		latest = frappe.db.get_value(
			"Employee Salary Revision", {"salary_profile": self.name},
			["name", "revision_number", "effective_from"], order_by="revision_number desc", as_dict=True,
		)
		if latest:
			frappe.db.set_value(
				"Employee Salary Revision", latest.name, "effective_to",
				add_days(self.effective_date, -1), update_modified=False,
			)
		revision = frappe.get_doc({
			"doctype": "Employee Salary Revision",
			"employee": self.employee,
			"employee_name": self.employee_name,
			"salary_profile": self.name,
			"revision_number": (latest.revision_number if latest else 0) + 1,
			"effective_from": self.effective_date,
			"action_date": self.action_date,
			"changed_by": frappe.session.user,
			"basic_salary": self.basic_salary,
			"transportation": self.transportation,
			"family_allowance": self.family_allowance,
			"total_salary": self.total_salary,
			"change_summary": self._change_summary(),
		})
		for component, (_amount_field, table_field) in COMPONENT_TABLES.items():
			for row in self.get(table_field):
				revision.append("allocations", {
					"component": component,
					"company": row.company,
					"account": row.account,
					"cost_center": row.cost_center,
					"amount": row.amount,
					"percentage": row.percentage,
				})
		revision.flags.ignore_permissions = True
		revision.insert()
		from accounting_custom.accounting.salary_payroll import sync_revision_to_hrms
		sync_revision_to_hrms(revision)
		return revision

	def _change_summary(self):
		before = self.get_doc_before_save()
		if not before:
			return _("Initial salary configuration")
		changes = []
		for label, fieldname in (
			(_("Effective Date"), "effective_date"),
			(_("Basic Salary"), "basic_salary"),
			(_("Transportation"), "transportation"),
			(_("Family Allowance"), "family_allowance"),
		):
			if before.get(fieldname) != self.get(fieldname):
				changes.append("{0}: {1} → {2}".format(label, before.get(fieldname) or 0, self.get(fieldname) or 0))
		return "; ".join(changes) or _("Allocation details changed")
