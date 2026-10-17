from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from accounting_custom.executive import (
	_active_employee_names,
	_employees_on_leave,
	_present_employee_names,
	_require_access,
	_scheduled_employee_names,
)


def execute(filters=None):
	_require_access()
	filters = frappe._dict(filters or {})
	category = filters.get("category") or "Active Employees"
	columns, data = _get_data(category, filters)
	return columns, data, None, None, _summary(category, data)


def _get_data(category, filters):
	if category == "Active Employees":
		return _employee_columns(), _employee_rows(_active_employee_names(filters.get("date")), filters)
	if category in ("Clocked In Today", "No Clock-in Today"):
		return _attendance(category, filters)
	if category == "Pending Leaves":
		return _pending_leaves(filters)
	if category == "Payroll YTD":
		return _payroll(filters)
	if category == "Donations YTD":
		return _donations(filters)
	masters = {
		"Donors": ("Donor", {}),
		"Beneficiaries": ("Beneficiary", {"status": "Active"}),
		"Orphans": ("Beneficiary", {"status": "Active", "father_status": "Dead"}),
		"Families": ("Family", {}),
		"Relief Orders": ("Relief Order", {"docstatus": ["<", 2]}),
		"Relief Statements": ("Relief Statement", {"docstatus": ["<", 2]}),
		"Beneficiary Activities": ("Beneficiary Activity", {"docstatus": ["<", 2]}),
	}
	if category in masters:
		doctype, query_filters = masters[category]
		return _master_rows(doctype, query_filters, filters)
	frappe.throw(_("Unsupported executive report category."))


def _employee_columns():
	return [
		{"fieldname": "reference", "label": _("Employee ID"), "width": 145},
		{"fieldname": "title", "label": _("Employee Name"), "width": 210},
		{"fieldname": "company", "label": _("Company"), "width": 170},
		{"fieldname": "status", "label": _("Status"), "width": 115},
		{"fieldname": "details", "label": _("Branch / Department"), "width": 260},
	]


def _employee_rows(names, filters):
	if not names:
		return []
	query_filters = {"name": ["in", list(names)]}
	if filters.get("company"):
		query_filters["company"] = filters.company
	rows = frappe.get_all("Employee", filters=query_filters, fields=["name", "employee_name", "company", "status", "branch", "department"], order_by="employee_name", limit_page_length=0)
	return [{"reference": row.name, "title": row.employee_name, "company": row.company, "status": row.status, "details": " · ".join(value for value in (row.branch, row.department) if value)} for row in rows]


def _attendance(category, filters):
	day = getdate(filters.get("date") or nowdate())
	active = _active_employee_names(day)
	present = _present_employee_names(day, active)
	if category == "Clocked In Today":
		names = present
		status = _("Clocked In")
	else:
		names = _scheduled_employee_names(day, active) - present - _employees_on_leave(day, active)
		status = _("No Clock-in")
	rows = _employee_rows(names, filters)
	if not rows:
		return _employee_columns(), []
	logs = frappe.db.sql(
		"""select employee, min(case when log_type='IN' then time end) first_in,
		max(case when log_type='OUT' then time end) last_out
		from `tabEmployee Checkin` where employee in %(employees)s
		and time >= %(start)s and time < %(end)s group by employee""",
		{"employees": tuple(names), "start": f"{day} 00:00:00", "end": f"{frappe.utils.add_days(day, 1)} 00:00:00"}, as_dict=True,
	)
	log_map = {row.employee: row for row in logs}
	for row in rows:
		log = log_map.get(row["reference"])
		row["status"] = status
		if log:
			row["details"] = _("First IN: {0} · Last OUT: {1}").format(log.first_in or "—", log.last_out or "—")
	return _employee_columns(), rows


def _pending_leaves(filters):
	conditions = ["la.docstatus=0", "coalesce(e.custom_is_payroll_identity,0)=0"]
	values = {}
	if filters.get("company"):
		conditions.append("la.company=%(company)s")
		values["company"] = filters.company
	rows = frappe.db.sql(f"""select la.name reference, e.employee_name title, la.company,
		la.status, concat(la.leave_type, ' · ', la.from_date, ' → ', la.to_date) details
		from `tabLeave Application` la join `tabEmployee` e on e.name=la.employee
		where {' and '.join(conditions)} order by la.from_date, e.employee_name""", values, as_dict=True)
	return _employee_columns(), rows


def _payroll(filters):
	from_date = filters.get("from_date") or f"{getdate(nowdate()).year}-01-01"
	to_date = filters.get("to_date") or nowdate()
	conditions = ["ss.docstatus=1", "ss.start_date >= %(from_date)s", "ss.end_date <= %(to_date)s"]
	values = {"from_date": from_date, "to_date": to_date}
	if filters.get("company"):
		conditions.append("ss.company=%(company)s")
		values["company"] = filters.company
	rows = frappe.db.sql(f"""select coalesce(e.custom_master_employee, ss.employee) reference,
		coalesce(master.employee_name, ss.employee_name) title,
		group_concat(distinct ss.company order by ss.company separator ', ') company,
		'Submitted' status, count(distinct ss.name) slips, sum(ss.gross_pay) gross_pay,
		sum(ss.total_deduction) deductions, sum(ss.net_pay) net_pay
		from `tabSalary Slip` ss join `tabEmployee` e on e.name=ss.employee
		left join `tabEmployee` master on master.name=coalesce(e.custom_master_employee, ss.employee)
		where {' and '.join(conditions)}
		group by coalesce(e.custom_master_employee, ss.employee), coalesce(master.employee_name, ss.employee_name)
		order by title""", values, as_dict=True)
	columns = _employee_columns()[:3] + [
		{"fieldname": "slips", "label": _("Salary Slips"), "fieldtype": "Int", "width": 105},
		{"fieldname": "gross_pay", "label": _("Gross Pay"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "deductions", "label": _("Deductions"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "net_pay", "label": _("Net Pay"), "fieldtype": "Currency", "width": 140},
	]
	return columns, rows


def _donations(filters):
	from_date = filters.get("from_date") or f"{getdate(nowdate()).year}-01-01"
	to_date = filters.get("to_date") or nowdate()
	query_filters = {"docstatus": 1, "posting_date": ["between", [from_date, to_date]]}
	if filters.get("company"):
		query_filters["company"] = filters.company
	fields = ["name", "posting_date", "company"]
	for field in ("donor", "total_usd", "total_lbp"):
		if frappe.get_meta("Donation Entry").has_field(field):
			fields.append(field)
	rows = frappe.get_all("Donation Entry", filters=query_filters, fields=fields, order_by="posting_date desc", limit_page_length=0)
	columns = [
		{"fieldname": "name", "label": _("Reference"), "width": 175},
		{"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 105},
		{"fieldname": "donor", "label": _("Donor"), "width": 190},
		{"fieldname": "company", "label": _("Company"), "width": 170},
		{"fieldname": "total_usd", "label": _("USD"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_lbp", "label": _("LBP"), "fieldtype": "Currency", "width": 150},
	]
	return columns, rows


def _master_rows(doctype, query_filters, filters):
	meta = frappe.get_meta(doctype)
	if filters.get("company") and meta.has_field("company"):
		query_filters["company"] = filters.company
	title_field = meta.title_field if meta.title_field and meta.has_field(meta.title_field) else "name"
	fields = ["name", title_field]
	for field in ("company", "status", "creation"):
		if meta.has_field(field) and field not in fields:
			fields.append(field)
	rows = frappe.get_all(doctype, filters=query_filters, fields=fields, order_by=f"{title_field} asc", limit_page_length=0)
	data = [{"reference": row.name, "title": row.get(title_field) or row.name, "company": row.get("company"), "status": row.get("status"), "details": row.get("creation")} for row in rows]
	return _employee_columns(), data


def _summary(category, data):
	return [{"value": len(data), "label": _(category), "datatype": "Int", "indicator": "Blue"}]
