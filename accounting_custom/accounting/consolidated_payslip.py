import frappe
from frappe.utils import flt


def sync_consolidated_payslip(master_employee, start_date, end_date):
	identities = frappe.get_all("Employee", filters={"custom_master_employee": master_employee}, pluck="name")
	identities.append(master_employee)
	slips = frappe.get_all(
		"Salary Slip",
		filters={"employee": ["in", list(set(identities))], "start_date": start_date, "end_date": end_date, "docstatus": ["<", 2]},
		fields=["name", "company", "currency", "gross_pay", "total_deduction", "net_pay", "docstatus"],
		order_by="company asc",
	)
	if not slips:
		return None
	currencies = {row.currency for row in slips}
	if len(currencies) != 1:
		return None
	name = f"CPS-{master_employee}-{start_date}-{end_date}"[:140]
	doc = frappe.get_doc("Employee Consolidated Payslip", name) if frappe.db.exists("Employee Consolidated Payslip", name) else frappe.new_doc("Employee Consolidated Payslip")
	doc.payslip_id = name
	doc.employee = master_employee
	employee_fields = ["employee_name", "designation"]
	if frappe.get_meta("Employee").has_field("custom_employee_name_ar"):
		employee_fields.append("custom_employee_name_ar")
	employee = frappe.db.get_value("Employee", master_employee, employee_fields, as_dict=True)
	doc.employee_name = employee.employee_name
	doc.employee_name_arabic = employee.get("custom_employee_name_ar") or employee.employee_name
	doc.designation = employee.designation
	doc.start_date = start_date
	doc.end_date = end_date
	doc.currency = slips[0].currency
	doc.gross_pay = sum(flt(row.gross_pay) for row in slips)
	doc.total_deduction = sum(flt(row.total_deduction) for row in slips)
	doc.net_pay = sum(flt(row.net_pay) for row in slips)
	for fieldname, amount in _component_totals([row.name for row in slips]).items():
		doc.set(fieldname, amount)
	doc.deduction_reasons = _deduction_reasons([row.name for row in slips], doc.currency)
	doc.company_count = len(slips)
	doc.status = "Submitted" if all(row.docstatus == 1 for row in slips) else "Partial"
	doc.set("companies", [])
	for row in slips:
		doc.append("companies", {"company": row.company, "salary_slip": row.name, "gross_pay": row.gross_pay, "total_deduction": row.total_deduction, "net_pay": row.net_pay, "slip_status": "Submitted" if row.docstatus == 1 else "Draft"})
	doc.flags.ignore_permissions = True
	doc.save()
	return doc.name


def _component_totals(salary_slips):
	totals = {
		"basic_salary": 0, "transportation": 0, "family_allowance": 0,
		"other_earnings": 0, "tax_deduction": 0,
		"advance_deduction": 0, "other_deduction": 0,
	}
	if not salary_slips:
		return totals
	for row in frappe.get_all(
		"Salary Detail",
		filters={"parent": ["in", salary_slips], "parenttype": "Salary Slip"},
		fields=["parentfield", "salary_component", "amount", "additional_salary"],
	):
		component = (row.salary_component or "").strip().lower()
		amount = flt(row.amount)
		if row.parentfield == "earnings":
			if component == "basic salary": totals["basic_salary"] += amount
			elif component == "transportation": totals["transportation"] += amount
			elif component == "family allowance": totals["family_allowance"] += amount
			else: totals["other_earnings"] += amount
		elif row.parentfield == "deductions":
			is_employee_advance = bool(
				row.additional_salary
				and frappe.db.get_value("Additional Salary", row.additional_salary, "ref_doctype") == "Employee Advance"
			)
			if "tax" in component or "ضريب" in component: totals["tax_deduction"] += amount
			elif is_employee_advance or any(token in component for token in ("advance", "loan", "سلف")): totals["advance_deduction"] += amount
			else: totals["other_deduction"] += amount
	return totals


def _deduction_reasons(salary_slips, currency):
	if not salary_slips:
		return ""
	rows = frappe.get_all(
		"Salary Detail",
		filters={"parent": ["in", salary_slips], "parenttype": "Salary Slip", "parentfield": "deductions"},
		fields=["salary_component", "amount", "additional_salary"],
	)
	additional_names = list({row.additional_salary for row in rows if row.additional_salary})
	reasons_by_additional = _additional_salary_reasons(additional_names)
	totals = {}
	for row in rows:
		reason = reasons_by_additional.get(row.additional_salary) or row.salary_component
		if reason:
			totals[reason] = totals.get(reason, 0) + flt(row.amount)
	return "\n".join(f"{reason}: {amount:,.0f} {currency}" for reason, amount in totals.items())


def _additional_salary_reasons(additional_names):
	if not additional_names:
		return {}
	additional_rows = frappe.get_all(
		"Additional Salary",
		filters={"name": ["in", additional_names]},
		fields=["name", "ref_doctype", "ref_docname"],
	)
	reasons = {
		row.additional_salary: row.note
		for row in frappe.get_all(
			"Payroll Manual Deduction",
			filters={"additional_salary": ["in", additional_names]},
			fields=["additional_salary", "note"],
		)
		if row.note
	}
	for source in additional_rows:
		if source.name in reasons or not source.ref_doctype or not source.ref_docname:
			continue
		if source.ref_doctype == "Employee Advance":
			reasons[source.name] = frappe.db.get_value("Employee Advance", source.ref_docname, "purpose")
		elif source.ref_doctype == "Employee Monthly Adjustment":
			adjustment = frappe.get_doc("Employee Monthly Adjustment", source.ref_docname)
			created = (adjustment.additional_salary_documents or "").splitlines()
			for additional_name, detail in zip(created, adjustment.deductions):
				if detail.note:
					reasons[additional_name] = detail.note
	return reasons


def sync_employee_payslips(master_employee):
	identities = frappe.get_all("Employee", filters={"custom_master_employee": master_employee}, pluck="name")
	identities.append(master_employee)
	periods = frappe.get_all("Salary Slip", filters={"employee": ["in", list(set(identities))], "docstatus": ["<", 2]}, fields=["start_date", "end_date"], distinct=True)
	for period in periods:
		sync_consolidated_payslip(master_employee, period.start_date, period.end_date)
	return frappe.get_all("Employee Consolidated Payslip", filters={"employee": master_employee}, fields=["name", "status", "start_date", "end_date", "currency", "gross_pay", "total_deduction", "net_pay", "company_count"], order_by="end_date desc", limit=12)
