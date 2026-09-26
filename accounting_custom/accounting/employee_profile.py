import frappe
from frappe import _
from frappe.utils import getdate


POSITION_FIELDS = ("company", "branch", "department", "designation", "employment_type", "from_date")


def validate_employee_accounting_profile(doc, method=None):
	if doc.get("custom_is_payroll_identity"):
		return
	_move_departed_positions(doc)
	positions = [row for row in (doc.get("custom_branches") or []) if row.company and row.branch]
	if not positions:
		if doc.status == "Active":
			frappe.throw(_("Please add at least one current position."))
		return

	_validate_unique_positions(positions)
	for row in positions:
		_validate_position_company(row)

	# HRMS remains synchronized with the first active company employment.
	primary = positions[0]
	doc.company = primary.company
	doc.branch = primary.branch
	doc.department = primary.department
	doc.designation = primary.designation
	doc.employment_type = primary.employment_type


def _move_departed_positions(doc):
	current_positions = []
	for row in doc.get("custom_branches") or []:
		if not row.left_position:
			current_positions.append(row)
			continue
		if not row.leaving_date:
			frappe.throw(_("Row {0}: Enter the To Date before leaving this position.").format(row.idx))
		if row.from_date and getdate(row.leaving_date) < getdate(row.from_date):
			frappe.throw(_("Row {0}: To Date cannot be before From Date.").format(row.idx))
		doc.append("custom_past_positions", {
			"company": row.company,
			"branch": row.branch,
			"department": row.department,
			"designation": row.designation,
			"employment_type": row.employment_type,
			"from_date": row.from_date,
			"to_date": row.leaving_date,
		})
	doc.set("custom_branches", current_positions)


def _validate_position_company(row):
	branch_company = frappe.db.get_value("Branch", row.branch, "custom_company")
	if branch_company and branch_company != row.company:
		frappe.throw(_("Row {0}: Branch {1} does not belong to company {2}.").format(row.idx, row.branch, row.company))
	if row.department:
		department_company = frappe.db.get_value("Department", row.department, "company")
		if department_company and department_company != row.company:
			frappe.throw(_("Row {0}: Department {1} does not belong to company {2}.").format(row.idx, row.department, row.company))


def _validate_unique_positions(positions):
	seen = set()
	for row in positions:
		key = tuple(row.get(fieldname) or "" for fieldname in POSITION_FIELDS)
		if key in seen:
			frappe.throw(_("Row {0}: This current position is duplicated.").format(row.idx))
		seen.add(key)


def sync_company_payroll_identities(doc, method=None):
	"""Maintain one internal ERPNext Employee per employing company."""
	if doc.get("custom_is_payroll_identity"):
		return
	positions_by_company = {}
	for row in doc.get("custom_branches") or []:
		positions_by_company.setdefault(row.company, row)
	active_companies = set(positions_by_company)
	for identity in frappe.get_all("Employee", filters={"custom_master_employee": doc.name}, fields=["name", "company"]):
		if identity.company not in active_companies:
			to_date = _latest_company_departure(doc, identity.company)
			frappe.db.set_value("Employee", identity.name, {"status": "Left", "relieving_date": to_date}, update_modified=False)
	for company, position in positions_by_company.items():
		identity = frappe.db.get_value("Employee", {"custom_master_employee": doc.name, "company": company}, "name")
		if identity:
			frappe.db.set_value("Employee", identity, {
				"status": doc.status, "relieving_date": None, "employee_name": doc.employee_name,
				"department": position.department,
				"designation": position.designation, "employment_type": position.employment_type,
				"branch": position.branch, "holiday_list": doc.holiday_list,
			}, update_modified=False)
			continue
		identity_doc = frappe.get_doc({
			"doctype": "Employee", "first_name": doc.employee_name, "middle_name": None,
			"last_name": None, "gender": doc.gender,
			"date_of_birth": doc.date_of_birth, "date_of_joining": position.from_date or doc.date_of_joining,
			"status": doc.status, "relieving_date": doc.relieving_date if doc.status == "Left" else None,
			"company": company, "branch": position.branch,
			"department": position.department, "designation": position.designation,
			"employment_type": position.employment_type, "holiday_list": doc.holiday_list, "custom_master_employee": doc.name,
			"custom_is_payroll_identity": 1,
		})
		identity_doc.flags.ignore_permissions = True
		abbr = frappe.db.get_value("Company", company, "abbr") or company[:8]
		identity_name = f"PAY-{doc.name}-{abbr}"[:140]
		identity_doc.insert(set_name=identity_name)


def get_payroll_employee(master_employee, company):
	return frappe.db.get_value("Employee", {"custom_master_employee": master_employee, "company": company}, "name")


def _latest_company_departure(doc, company):
	dates = [row.to_date for row in doc.get("custom_past_positions") or [] if row.company == company and row.to_date]
	return max(dates) if dates else None


def normalize_payroll_identity_titles():
	"""Use the master employee title for hidden payroll identities."""
	for identity in frappe.get_all(
		"Employee",
		filters={"custom_is_payroll_identity": 1},
		fields=["name", "custom_master_employee"],
	):
		master_name = frappe.db.get_value("Employee", identity.custom_master_employee, "employee_name")
		if master_name:
			frappe.db.set_value("Employee", identity.name, "employee_name", master_name, update_modified=False)
