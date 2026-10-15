from datetime import date
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


def _metrics():
	today = nowdate()
	year_start = f"{date.today().year}-01-01"
	return {
		"companies": _count("Company", {"is_group": 0}),
		"employees": _count("Employee"),
		"active_employees": _count("Employee", {"status": "Active"}),
		"pending_leaves": _count("Leave Application", {"docstatus": 0}),
		"attendance_today": _count("Attendance", {"attendance_date": today, "docstatus": 1}),
		"absent_today": _count("Attendance", {"attendance_date": today, "status": "Absent", "docstatus": 1}),
		"payroll_ytd": _sum("Salary Slip", "net_pay", {"start_date": [">=", year_start], "docstatus": 1}),
		"donors": _count("Donor"),
		"donations": _count("Donation Entry", {"docstatus": 1}),
		"donations_usd": _sum("Donation Entry", "total_usd", {"docstatus": 1, "posting_date": [">=", year_start]}),
		"donations_lbp": _sum("Donation Entry", "total_lbp", {"docstatus": 1, "posting_date": [">=", year_start]}),
		"beneficiaries": _count("Beneficiary", {"status": "Active"}),
		"orphans": _count("Beneficiary", {"status": "Active", "father_status": "Dead"}),
		"families": _count("Family"),
		"relief_orders": _count("Relief Order"),
		"relief_statements": _count("Relief Statement"),
		"activities": _count("Beneficiary Activity"),
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
	attendance = [
		{"label": status, "value": _count("Attendance", {"attendance_date": nowdate(), "status": status, "docstatus": 1})}
		for status in ("Present", "Absent", "On Leave", "Half Day", "Work From Home")
	]
	companies = frappe.get_all("Company", filters={"is_group": 0}, fields=["name", "default_currency"], order_by="name") if _exists("Company") else []
	return {
		"metrics": _metrics(),
		"attendance": attendance,
		"leave_trend": _monthly_series("Leave Application", "from_date", filters={"docstatus": ["<", 2]}),
		"donation_usd_trend": _monthly_series("Donation Entry", "posting_date", "total_usd", filters={"docstatus": 1}),
		"donation_lbp_trend": _monthly_series("Donation Entry", "posting_date", "total_lbp", filters={"docstatus": 1}),
		"companies": companies,
		"company_finance": _company_finance(),
		"reports": _reports(),
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
			on gle.company = c.name and gle.is_cancelled = 0
		left join `tabAccount` a on a.name = gle.account
		where coalesce(c.is_group, 0) = 0
		group by c.name, c.default_currency
		order by c.name
		""",
		{"year_start": year_start},
		as_dict=True,
	)


def _reports():
	groups = {
		"HR & Payroll": ["Employee", "Leave Application", "Attendance", "Salary Slip", "Payroll Entry", "Employee Salary History"],
		"Accounting": ["General Ledger", "Trial Balance", "Balance Sheet", "Profit and Loss Statement", "Daily Treasury Report", "All Daily Movement", "Monthly Cash Bank Balance", "Balance Sheet by Cost Center"],
		"Donations": ["Donation Entry", "Donor", "Donor Donation History", "Collector Collections", "Project Donation Summary"],
		"Relief": ["Beneficiary", "Family", "Relief Order", "Relief Statement", "Beneficiary Activity", "Beneficiary-wise Sponsors", "Sponsor-wise Beneficiary", "Orphan Balance", "Donation Report"],
	}
	result = []
	for group, names in groups.items():
		items = []
		for name in names:
			if frappe.db.exists("Report", name):
				items.append({"label": name, "route": f"/app/query-report/{quote(name)}"})
			elif frappe.db.exists("DocType", name):
				items.append({"label": name, "route": f"/app/{frappe.scrub(name).replace('_', '-')}"})
		result.append({"group": group, "items": items})
	return result
