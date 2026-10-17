from datetime import date, timedelta
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, get_last_day, nowdate


ROLE = "Group CEO"


def _require_access():
	if frappe.session.user != "Administrator" and ROLE not in frappe.get_roles():
		frappe.throw(_("Group CEO access is required."), frappe.PermissionError)


def _exists(doctype):
	return bool(frappe.db.exists("DocType", doctype) and frappe.db.table_exists(doctype))


def _count(doctype, filters=None):
	return frappe.db.count(doctype, filters or {}) if _exists(doctype) else 0


def _sum(doctype, field, filters=None):
	if not _exists(doctype) or not frappe.get_meta(doctype).has_field(field):
		return 0
	return flt(frappe.db.get_value(doctype, filters or {}, f"sum({field})") or 0)


def _active_employee_names(today=None):
	"""Active people only; company-specific payroll identity rows are excluded."""
	today = frappe.utils.getdate(today or nowdate())
	rows = frappe.get_all(
		"Employee",
		filters={
			"status": "Active",
			"date_of_joining": ["<=", today],
			"custom_is_payroll_identity": 0,
		},
		fields=["name", "relieving_date"],
		limit_page_length=0,
	)
	return {
		row.name for row in rows
		if not row.name.startswith("_T-")
		and (not row.relieving_date or frappe.utils.getdate(row.relieving_date) >= today)
	}


def _present_employee_names(today=None, employees=None):
	"""A single IN punch is enough to be present; OUT is not required."""
	today = frappe.utils.getdate(today or nowdate())
	employees = employees if employees is not None else _active_employee_names(today)
	if not employees or not _exists("Employee Checkin"):
		return set()
	return set(frappe.get_all(
		"Employee Checkin",
		filters=[
			["employee", "in", list(employees)],
			["log_type", "=", "IN"],
			["time", ">=", f"{today} 00:00:00"],
			["time", "<", f"{today + timedelta(days=1)} 00:00:00"],
		],
		pluck="employee",
		distinct=True,
		limit_page_length=0,
	))


def _scheduled_employee_names(today=None, employees=None):
	"""Employees expected to work today, excluding holidays and rest days."""
	today = frappe.utils.getdate(today or nowdate())
	employees = employees if employees is not None else _active_employee_names(today)
	try:
		from hr_custom.services.work_schedule import get_holiday_status, get_scheduled_period
	except ImportError:
		return set(employees)
	scheduled = set()
	for employee in employees:
		try:
			period = get_scheduled_period(employee, today)
			if flt(period.get("working_hours")) > 0 and not get_holiday_status(employee, today):
				scheduled.add(employee)
		except Exception:
			# Legacy employees without a schedule remain visible rather than being
			# silently omitted from attendance oversight.
			scheduled.add(employee)
	return scheduled


def _employees_on_leave(today=None, employees=None):
	today = frappe.utils.getdate(today or nowdate())
	employees = employees if employees is not None else _active_employee_names(today)
	if not employees:
		return set()
	return set(frappe.get_all(
		"Leave Application",
		filters={
			"employee": ["in", list(employees)], "docstatus": 1, "status": "Approved",
			"from_date": ["<=", today], "to_date": [">=", today],
		},
		pluck="employee",
		distinct=True,
		limit_page_length=0,
	))


def _pending_real_employee_leaves():
	if not _exists("Leave Application"):
		return 0
	return frappe.db.sql(
		"""select count(*) from `tabLeave Application` la
		join `tabEmployee` e on e.name = la.employee
		where la.docstatus = 0 and coalesce(e.custom_is_payroll_identity, 0) = 0"""
	)[0][0] or 0


def _current_user_employee_names():
	"""Return real Employee profiles linked to the current Desk user."""
	if frappe.session.user in ("Guest", "Administrator"):
		return []
	return frappe.get_all(
		"Employee",
		filters={"user_id": frappe.session.user, "custom_is_payroll_identity": 0},
		pluck="name",
		limit_page_length=0,
	)


def _my_pending_leave_approvals():
	employees = _current_user_employee_names()
	if not employees:
		return 0
	return frappe.db.count("Leave Application", {
		"docstatus": 0,
		"custom_approval_stage": "Pending Approver Approval",
		"custom_current_approver": ["in", employees],
	})


def _metrics():
	today = nowdate()
	year_start = f"{date.today().year}-01-01"
	active = _active_employee_names(today)
	present = _present_employee_names(today, active)
	on_leave = _employees_on_leave(today, active) - present
	scheduled = _scheduled_employee_names(today, active)
	return {
		"companies": _count("Company", {"is_group": 0}),
		"employees": _count("Employee", {"custom_is_payroll_identity": 0}),
		"active_employees": len(active),
		"pending_leaves": _pending_real_employee_leaves(),
		"my_leave_approvals": _my_pending_leave_approvals(),
		"attendance_today": len(present),
		"absent_today": len(scheduled - present - on_leave),
		"on_leave_today": len(on_leave),
		"payroll_ytd": _sum("Salary Slip", "net_pay", {"start_date": [">=", year_start], "end_date": ["<=", today], "docstatus": 1}),
		"donors": _count("Donor"),
		"donations": _count("Donation Entry", {"docstatus": 1, "posting_date": ["between", [year_start, today]]}),
		"donations_usd": _sum("Donation Entry", "total_usd", {"docstatus": 1, "posting_date": ["between", [year_start, today]]}),
		"donations_lbp": _sum("Donation Entry", "total_lbp", {"docstatus": 1, "posting_date": ["between", [year_start, today]]}),
		"beneficiaries": _count("Beneficiary", {"status": "Active"}),
		"orphans": _count("Beneficiary", {"status": "Active", "father_status": "Dead"}),
		"families": _count("Family"),
		"relief_orders": _count("Relief Order", {"docstatus": ["<", 2]}),
		"relief_statements": _count("Relief Statement", {"docstatus": ["<", 2]}),
		"activities": _count("Beneficiary Activity", {"docstatus": ["<", 2]}),
	}


@frappe.whitelist()
def number_card(filters=None):
	_require_access()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	metric = filters.get("metric")
	value = _metrics().get(metric, 0)
	return {"value": value, "fieldtype": "Currency" if metric == "payroll_ytd" else "Int", "route": ["group-ceo-dashboard"]}


def _monthly_series(doctype, date_field, value_field=None, months=6, filters=None):
	labels, values = [], []
	for offset in range(months - 1, -1, -1):
		month = add_months(nowdate(), -offset)
		labels.append(frappe.utils.getdate(month).strftime("%b"))
		period_filters = dict(filters or {})
		period_filters[date_field] = ["between", [get_first_day(month), get_last_day(month)]]
		values.append(_sum(doctype, value_field, period_filters) if value_field else _count(doctype, period_filters))
	return {"labels": labels, "values": values}


@frappe.whitelist()
def get_dashboard_data():
	_require_access()
	metrics = _metrics()
	attendance = [
		{"label": "Clocked In", "value": metrics["attendance_today"]},
		{"label": "Approved Leave", "value": metrics["on_leave_today"]},
		{"label": "No Clock-in", "value": metrics["absent_today"]},
	]
	companies = frappe.get_all("Company", filters={"is_group": 0}, fields=["name", "default_currency"], order_by="name") if _exists("Company") else []
	return {
		"metrics": metrics,
		"attendance": attendance,
		"leave_trend": _monthly_series("Leave Application", "from_date", filters={"docstatus": ["<", 2]}),
		"donation_usd_trend": _monthly_series("Donation Entry", "posting_date", "total_usd", filters={"docstatus": 1}),
		"donation_lbp_trend": _monthly_series("Donation Entry", "posting_date", "total_lbp", filters={"docstatus": 1}),
		"companies": companies,
		"company_finance": _company_finance(),
		"routes": _metric_routes(),
		"reports": _reports(),
	}


def _metric_routes():
	today = nowdate()
	year_start = f"{date.today().year}-01-01"
	report_route = ["query-report", "Group CEO Executive Report"]

	def report(category, **filters):
		return {"route": report_route, "filters": {"category": category, **filters}}

	return {
		"active_employees": report("Active Employees", date=today),
		"pending_leaves": report("Pending Leaves"),
		"my_leave_approvals": report("My Pending Leave Approvals"),
		"attendance_today": report("Clocked In Today", date=today),
		"absent_today": report("No Clock-in Today", date=today),
		"payroll_ytd": report("Payroll Since January 1", from_date=year_start, to_date=today),
		"donors": report("Donors"),
		"beneficiaries": report("Beneficiaries"),
		"orphans": report("Orphans"),
		"families": report("Families"),
		"relief_orders": report("Relief Orders"),
		"relief_statements": report("Relief Statements"),
		"activities": report("Beneficiary Activities"),
		"donations": report("Donations Since January 1", from_date=year_start, to_date=today),
	}


def _company_finance():
	"""Return comparable YTD P&L and current liquid balances per company."""
	if not (_exists("GL Entry") and _exists("Account") and _exists("Company")):
		return []
	year_start = f"{date.today().year}-01-01"
	return frappe.db.sql(
		"""
		select
			c.name as company,
			c.default_currency as currency,
			coalesce(sum(case
				when gle.posting_date >= %(year_start)s and a.root_type = 'Income'
				then gle.credit - gle.debit else 0 end), 0) as income_ytd,
			coalesce(sum(case
				when gle.posting_date >= %(year_start)s and a.root_type = 'Expense'
				then gle.debit - gle.credit else 0 end), 0) as expense_ytd,
			coalesce(sum(case
				when a.account_type in ('Cash', 'Bank')
				then gle.debit - gle.credit else 0 end), 0) as cash_bank
		from `tabCompany` c
		left join `tabGL Entry` gle
			on gle.company = c.name and gle.is_cancelled = 0 and gle.posting_date <= %(today)s
		left join `tabAccount` a on a.name = gle.account
		where coalesce(c.is_group, 0) = 0
		group by c.name, c.default_currency
		order by c.name
		""",
		{"year_start": year_start, "today": nowdate()},
		as_dict=True,
	)


def _reports():
	groups = {
		"Executive Overview": ["Group CEO Executive Report", "Daily Attendance Overview"],
		"HR & Payroll": ["Weekly Employee Hours", "Hourly Leave Balance"],
		"Accounting": ["General Ledger", "Trial Balance", "Balance Sheet", "Profit and Loss Statement", "Daily Treasury Report", "All Daily Movement", "Monthly Cash Bank Balance", "Balance Sheet by Cost Center"],
		"Donations": ["Donor Donation History", "Collector Collections", "Project Donation Summary"],
		"Relief": ["Beneficiary-wise Sponsors", "Sponsor-wise Beneficiary", "Orphan Balance", "Donation Report"],
	}
	result = []
	for group, names in groups.items():
		items = []
		for name in names:
			if frappe.db.exists("Report", name):
				items.append({"label": name, "route": f"/app/query-report/{quote(name)}"})
		if items:
			result.append({"group": group, "items": items})
	return result
