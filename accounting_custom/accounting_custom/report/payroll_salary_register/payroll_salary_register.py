import hashlib

import frappe
from frappe import _
from frappe.utils import flt


PAYROLL_CATEGORIES = (
	"دعاة",
	"خدمات",
	"منتديات",
	"نماء",
	"اداريين",
	"دور القران -اداريين",
	"دور-الشيوخ المدرسين",
)

STATIC_REGISTERS = {
	"مسجد الفرقان": {
		"title": "كشف رواتب الموظفين (مسجد الفرقان - عرمون)",
		"title_en": "Employee Salary Register (Al Furqan Mosque - Aramoun)",
		"columns": ("position", "basic_usd", "transportation", "family_allowance"),
		"rows": (
			{"employee_name": "الشيخ علاء العماري", "position": "إمام", "basic_usd": 200, "transportation": 60, "family_allowance": 100, "total": 360, "notes": "يتم تأمين الرواتب والإعانة من تبرعات المسجد"},
			{"employee_name": "عبيدة الأحمد", "position": "خادم", "basic_usd": 300, "family_allowance": 50, "total": 350, "notes": "يتم تأمين الرواتب والإعانة من تبرعات المسجد"},
		),
	},
	"مسجد أبي بكر الصديق": {
		"title": "كشف رواتب الموظفين (مسجد ومركز الخليفة الصديق أبي بكر رضي الله عنه)",
		"title_en": "Employee Salary Register (Caliph Abu Bakr Al-Siddiq Mosque and Center)",
		"columns": ("basic_usd", "family_allowance"),
		"rows": (
			{"employee_name": "محمد الصالح", "basic_usd": 800, "family_allowance": 100, "total": 900, "notes": "يتم تأمين الرواتب والإعانة من تبرعات المسجد"},
			{"employee_name": "مصطفى شعر", "basic_usd": 500, "family_allowance": 100, "total": 600, "notes": "يتم تأمين الرواتب والإعانة من تبرعات المسجد"},
			{"employee_name": "خضر العاصمي", "basic_usd": 400, "total": 400},
			{"employee_name": "عمر صبح", "basic_usd": 250, "total": 250, "notes": "موظف صيانة و خادم"},
			{"employee_name": "محمد جنون", "basic_usd": 50, "total": 50, "notes": "موظف خدمات"},
		),
	},
	"مسجد السيدة عائشة": {
		"title": "كشف رواتب الموظفين (مسجد عائشة أم المؤمنين)",
		"title_en": "Employee Salary Register (Aisha Mother of Believers Mosque)",
		"columns": ("basic_usd", "family_allowance", "deduction"),
		"rows": (
			{"employee_name": "فارس جمال الدين", "basic_usd": 300, "family_allowance": 100, "total": 400, "notes": "يتم تأمين الرواتب والإعانة من تبرعات المسجد"},
			{"employee_name": "عبود عبدالسلام منلا", "basic_usd": 150, "family_allowance": 50, "total": 200, "notes": "يتم تأمين الرواتب والإعانة من تبرعات المسجد"},
		),
	},
}

ARABIC_MONTHS = {
	"January": "كانون الثاني", "February": "شباط", "March": "آذار",
	"April": "نيسان", "May": "أيار", "June": "حزيران", "July": "تموز",
	"August": "آب", "September": "أيلول", "October": "تشرين الأول",
	"November": "تشرين الثاني", "December": "كانون الأول",
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.payroll_run:
		frappe.throw(_("Select a Multi Company Payroll Run."))

	run = frappe.get_doc("Multi Company Payroll Run", filters.payroll_run)
	run.check_permission("read")
	category = filters.payroll_category or ""
	if category and category not in (*PAYROLL_CATEGORIES, "غير مصنف", *STATIC_REGISTERS):
		frappe.throw(_("Invalid payroll category."))
	if category in STATIC_REGISTERS:
		return _static_register(run, category)

	employee_profiles = _get_employee_profiles(run)
	employees = list(run.employees)
	if category:
		employees = [
			row for row in employees
			if (employee_profiles.get(row.employee, {}).get("category") or "غير مصنف") == category
		]
	if category in ("اداريين", "منتديات"):
		employees.sort(key=lambda row: (
			_employee_subcategory(employee_profiles.get(row.employee), category),
			(employee_profiles.get(row.employee) or {}).get("arabic_name") or row.employee_name or "",
		))

	allocations = [
		row for row in run.allocation_summary
		if any(row.employee == employee.employee and row.company == employee.company for employee in employees)
	]
	cost_centers = _ordered_cost_centers(allocations)
	labels = _cost_center_labels(cost_centers)
	columns = _columns(cost_centers, labels, category)
	manual = _manual_deduction_totals(run)
	deduction_notes = _deduction_notes(run)
	data = []

	for index, employee in enumerate(employees, 1):
		key = (employee.employee, employee.company)
		rows = [row for row in allocations if (row.employee, row.company) == key]
		basic = [row for row in rows if row.component == "Basic Salary"]
		transportation = sum(flt(row.amount) for row in rows if row.component == "Transportation")
		family = sum(flt(row.amount) for row in rows if row.component == "Family Allowance")
		manual_deduction = manual.get(key, 0)
		advance = max(flt(employee.deductions) - manual_deduction, 0)
		notes = list(deduction_notes.get(key, ()))
		if advance:
			notes.append(f"سلفة: {_format_note_amount(advance)}")
		profile = employee_profiles.get(employee.employee) or {}
		result = {
			"company": employee.company,
			"row_number": str(index),
			"employee": employee.employee,
			"employee_name": profile.get("arabic_name") or employee.employee_name,
			"payroll_category": profile.get("category") or "غير مصنف",
			"sub_category": _employee_subcategory(profile, category),
			"basic_total": _blank_zero(sum(flt(row.amount) for row in basic)),
			"transportation": _blank_zero(transportation),
			"family_allowance": _blank_zero(family),
			"deduction": _blank_zero(manual_deduction),
			"advance": _blank_zero(advance),
			"net_salary": _blank_zero(flt(employee.pay_this_run)),
			"notes": " | ".join(notes),
		}
		for cost_center in cost_centers:
			result[_cost_center_field(cost_center)] = _blank_zero(sum(
				flt(row.amount) for row in basic if row.cost_center == cost_center
			))
		data.append(result)

	month = ARABIC_MONTHS.get(run.payroll_month, run.payroll_month)
	title = f"رواتب شهر {month} {run.payroll_year}"
	if category:
		title = f"{title} — {category}"
	if not _is_arabic():
		title = f"{run.payroll_month} {run.payroll_year} Payroll"
		if category:
			title = f"{title} — {_category_label(category)}"
	message = f'<div dir="{_direction()}" style="font-size:18px;font-weight:700;text-align:center">{frappe.utils.escape_html(title)}</div>'
	return columns, data, message, None, _summary(data)


def _get_employee_profiles(run):
	names = list({row.employee for row in run.employees if row.employee})
	if not names:
		return {}
	fields = ["name", "custom_payroll_category", "custom_admin_department", "custom_forum_institution"]
	if frappe.get_meta("Employee").has_field("custom_employee_name_ar"):
		fields.append("custom_employee_name_ar")
	return {
		row.name: {
			"category": row.custom_payroll_category,
			"admin_department": row.custom_admin_department,
			"forum_institution": row.custom_forum_institution,
			"arabic_name": row.get("custom_employee_name_ar"),
		}
		for row in frappe.get_all(
			"Employee",
			filters={"name": ["in", names]},
			fields=fields,
		)
	}


def _employee_subcategory(profile, category):
	profile = profile or {}
	if category == "اداريين":
		return profile.get("admin_department") or "غير محدد"
	if category == "منتديات":
		return profile.get("forum_institution") or "غير محدد"
	return ""


def _ordered_cost_centers(allocations):
	return list(dict.fromkeys(row.cost_center for row in allocations if row.cost_center))


def _cost_center_labels(cost_centers):
	if not cost_centers:
		return {}
	rows = frappe.get_all(
		"Cost Center",
		filters={"name": ["in", cost_centers]},
		fields=["name", "custom_cost_center_name_arabic", "cost_center_name"],
	)
	return {
		row.name: (
			row.custom_cost_center_name_arabic or row.cost_center_name or row.name
			if _is_arabic() else row.cost_center_name or row.name
		)
		for row in rows
	}


def _cost_center_field(cost_center):
	return "cost_center_" + hashlib.sha1(cost_center.encode()).hexdigest()[:10]


def _columns(cost_centers, labels, category=None):
	columns = [
		{"fieldname": "row_number", "label": "#", "fieldtype": "Data", "width": 45},
		{"fieldname": "employee_name", "label": _label("اسم الموظف", "Employee Name"), "fieldtype": "Data", "width": 180},
	]
	if category in ("اداريين", "منتديات"):
		columns.append({
			"fieldname": "sub_category",
			"label": "الادارة" if category == "اداريين" else "المؤسسة",
			"fieldtype": "Data",
			"width": 145,
		})
	columns.extend(
		{"fieldname": _cost_center_field(cost_center), "label": labels.get(cost_center, cost_center), "fieldtype": "Currency", "width": 115}
		for cost_center in cost_centers
	)
	columns.extend([
		{"fieldname": "basic_total", "label": _label("المجموع", "Basic Total"), "fieldtype": "Currency", "width": 105},
		{"fieldname": "transportation", "label": _label("المواصلات", "Transportation"), "fieldtype": "Currency", "width": 105},
		{"fieldname": "family_allowance", "label": _label("إعانة اجتماعية", "Social Allowance"), "fieldtype": "Currency", "width": 115},
		{"fieldname": "deduction", "label": _label("حسم", "Deductions"), "fieldtype": "Currency", "width": 90},
		{"fieldname": "advance", "label": _label("سلفة", "Advance"), "fieldtype": "Currency", "width": 90},
		{"fieldname": "net_salary", "label": _label("المستحق مع الإعانة", "Net Pay"), "fieldtype": "Currency", "width": 125},
		{"fieldname": "notes", "label": _label("ملاحظات", "Notes"), "fieldtype": "Data", "width": 180},
	])
	return columns


def _manual_deduction_totals(run):
	totals = {}
	for row in run.manual_deductions:
		key = (row.employee, row.company)
		totals[key] = totals.get(key, 0) + flt(row.amount)
	return totals


def _deduction_notes(run):
	"""Return the human-readable reason for each manual deduction in the register."""
	notes = {}
	for row in run.manual_deductions:
		key = (row.employee, row.company)
		label = (row.get("note") or row.get("salary_component") or row.get("source_component") or "حسم").strip()
		text = f"{label}: {_format_note_amount(row.amount)}"
		if text not in notes.setdefault(key, []):
			notes[key].append(text)
	return notes


def _format_note_amount(value):
	value = flt(value)
	return f"{value:,.2f}".rstrip("0").rstrip(".")


def _summary(data):
	return [
		{"value": len(data), "indicator": "Blue", "label": _("Employees"), "datatype": "Int"},
		{"value": sum(flt(row.get("net_salary")) for row in data), "indicator": "Green", "label": _("Net Payroll"), "datatype": "Currency"},
	]


def _blank_zero(value):
	value = flt(value)
	return None if abs(value) < 0.000001 else value


def _static_register(run, register_name):
	register = STATIC_REGISTERS[register_name]
	rows = []
	for index, source in enumerate(register["rows"], 1):
		row = {
			"row_number": str(index),
			"employee_name": source["employee_name"],
			"position": source.get("position", ""),
			"basic_lbp": _blank_zero(source.get("basic_lbp")),
			"basic_usd": _blank_zero(source.get("basic_usd")),
			"additional_usd": _blank_zero(source.get("additional_usd")),
			"transportation": _blank_zero(source.get("transportation")),
			"family_allowance": _blank_zero(source.get("family_allowance")),
			"deduction": _blank_zero(source.get("deduction")),
			"total": _blank_zero(source.get("total")),
			"notes": source.get("notes", ""),
		}
		rows.append(row)
	month = ARABIC_MONTHS.get(run.payroll_month, run.payroll_month)
	if _is_arabic():
		title = f'{register["title"]}<br>لشهر {month} {run.payroll_year}'
	else:
		title = f'{register["title_en"]}<br>For {run.payroll_month} {run.payroll_year}'
	message = f'<div dir="{_direction()}" style="font-size:20px;font-weight:700;text-align:center;line-height:1.8">{title}</div>'
	return _static_columns(register["columns"]), rows, message, None, [
		{"value": len(rows), "indicator": "Blue", "label": _("Employees"), "datatype": "Int"},
		{"value": sum(flt(row["total"]) for row in rows), "indicator": "Green", "label": _("Total"), "datatype": "Float"},
	]


def _static_columns(optional_fields):
	definitions = {
		"position": {"fieldname": "position", "label": _label("الوظيفة", "Position"), "fieldtype": "Data", "width": 100},
		"basic_lbp": {"fieldname": "basic_lbp", "label": _label("الراتب الأساسي ل.ل.", "Basic Salary LBP"), "fieldtype": "Float", "precision": 0, "width": 120},
		"basic_usd": {"fieldname": "basic_usd", "label": _label("الراتب الأساسي $", "Basic Salary USD"), "fieldtype": "Float", "precision": 0, "width": 120},
		"additional_usd": {"fieldname": "additional_usd", "label": _label("بدلات إضافية $", "Additional Allowance USD"), "fieldtype": "Float", "precision": 0, "width": 115},
		"transportation": {"fieldname": "transportation", "label": _label("المواصلات", "Transportation"), "fieldtype": "Float", "precision": 0, "width": 100},
		"family_allowance": {"fieldname": "family_allowance", "label": _label("الإعانة الاجتماعية", "Social Allowance"), "fieldtype": "Float", "precision": 0, "width": 120},
		"deduction": {"fieldname": "deduction", "label": _label("حسم $", "Deduction USD"), "fieldtype": "Float", "precision": 0, "width": 95},
	}
	columns = [
		{"fieldname": "row_number", "label": _label("رقم مسلسل", "No."), "fieldtype": "Data", "width": 85},
		{"fieldname": "employee_name", "label": _label("الاسم", "Name"), "fieldtype": "Data", "width": 180},
	]
	columns.extend(definitions[fieldname] for fieldname in optional_fields)
	columns.extend([
		{"fieldname": "total", "label": _label("الإجمالي $", "Total USD"), "fieldtype": "Float", "precision": 0, "width": 105},
		{"fieldname": "notes", "label": _label("ملاحظات", "Notes"), "fieldtype": "Data", "width": 260},
	])
	return columns


def _is_arabic():
	if getattr(frappe.flags, "payroll_register_force_arabic", False):
		return True
	return (getattr(frappe.local, "lang", None) or frappe.defaults.get_user_default("language") or "en").startswith("ar")


def _direction():
	return "rtl" if _is_arabic() else "ltr"


def _label(arabic, english):
	return arabic if _is_arabic() else english


def _category_label(category):
	labels = {
		"دعاة": "Preachers", "خدمات": "Services", "منتديات": "Forums", "نماء": "Namaa",
		"اداريين": "Administrators", "دور القران -اداريين": "Quran Centers - Administrators",
		"دور-الشيوخ المدرسين": "Quran Centers - Teachers", "غير مصنف": "Uncategorized",
		"مسجد الفرقان": "Al Furqan Mosque", "مسجد أبي بكر الصديق": "Abu Bakr Al-Siddiq Mosque",
		"مسجد السيدة عائشة": "Aisha Mosque",
	}
	return labels.get(category, category)


@frappe.whitelist()
def get_all_registers(payroll_run):
	previous = getattr(frappe.flags, "payroll_register_force_arabic", False)
	frappe.flags.payroll_register_force_arabic = True
	try:
		registers = []
		for category in (*PAYROLL_CATEGORIES, "غير مصنف", *STATIC_REGISTERS):
			columns, data, message, _chart, _summary_values = execute({
				"payroll_run": payroll_run,
				"payroll_category": category,
			})
			registers.append({
				"category": category,
				"category_label": category,
				"columns": columns,
				"data": data,
				"title_html": message,
			})
		return {"direction": "rtl", "registers": registers}
	finally:
		frappe.flags.payroll_register_force_arabic = previous
