import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_validate_filters(filters)
	rows = _get_gl_rows(filters)
	data = _build_data(rows, bool(filters.get("show_zero_values")))
	return _get_columns(), data, None, None, _get_summary(data, filters), True


def _get_columns():
	return [
		{"label": _("Account"), "fieldname": "account_number", "fieldtype": "Data", "width": 145},
		{"label": _("Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 260},
		{"label": _("Cost Center"), "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 280},
		{"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "options": "currency", "width": 170},
		{"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "options": "currency", "width": 170},
		{"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "options": "currency", "width": 180},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "hidden": 1},
		{"label": _("Row ID"), "fieldname": "row_id", "fieldtype": "Data", "hidden": 1},
		{"label": _("Parent Row ID"), "fieldname": "parent_row_id", "fieldtype": "Data", "hidden": 1},
		{"label": _("Indent"), "fieldname": "indent", "fieldtype": "Int", "hidden": 1},
	]


def _validate_filters(filters):
	if filters.get("fiscal_year"):
		dates = frappe.db.get_value(
			"Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"], as_dict=True
		)
		if dates:
			filters.from_date = filters.get("from_date") or dates.year_start_date
			filters.to_date = filters.get("to_date") or dates.year_end_date

	if filters.get("from_date") and filters.get("to_date"):
		if getdate(filters.from_date) > getdate(filters.to_date):
			frappe.throw(_("From Date cannot be later than To Date."))

	filters.from_account_number = (filters.get("from_account_number") or "").replace(" ", "").strip()
	filters.to_account_number = (filters.get("to_account_number") or "").replace(" ", "").strip()
	if filters.from_account_number and filters.to_account_number:
		if len(filters.from_account_number) != len(filters.to_account_number):
			frappe.throw(_("From Account Number and To Account Number must contain the same number of characters."))
		if filters.from_account_number > filters.to_account_number:
			frappe.throw(_("From Account Number cannot be greater than To Account Number."))


def _get_gl_rows(filters):
	conditions = ["gle.is_cancelled = 0", "IFNULL(gle.cost_center, '') != ''"]
	values = {
		"from_date": filters.get("from_date") or "0001-01-01",
		"to_date": filters.get("to_date") or "9999-12-31",
		"has_from_date": int(bool(filters.get("from_date"))),
		"include_opening_closing": int(filters.get("with_period_closing_entry_for_opening", 1)),
		"include_period_closing": int(filters.get("with_period_closing_entry_for_current_period", 1)),
	}

	if filters.get("company"):
		conditions.append("gle.company = %(company)s")
		values["company"] = filters.company
	if filters.get("to_date"):
		conditions.append("gle.posting_date <= %(to_date)s")

	if filters.get("cost_center"):
		center = frappe.db.get_value("Cost Center", filters.cost_center, ["company", "lft", "rgt"], as_dict=True)
		if not center:
			frappe.throw(_("The selected Cost Center does not exist."))
		if filters.get("company") and center.company != filters.company:
			frappe.throw(_("The selected Cost Center does not belong to company {0}.").format(filters.company))
		conditions.append("cc.company = %(cost_center_company)s AND cc.lft >= %(cost_center_lft)s AND cc.rgt <= %(cost_center_rgt)s")
		values.update(cost_center_company=center.company, cost_center_lft=center.lft, cost_center_rgt=center.rgt)

	range_length = len(filters.from_account_number or filters.to_account_number or "")
	if filters.from_account_number:
		conditions.append("LEFT(acc.account_number, %(range_length)s) >= %(from_account_number)s")
		values.update(range_length=range_length, from_account_number=filters.from_account_number)
	if filters.to_account_number:
		conditions.append("LEFT(acc.account_number, %(range_length)s) <= %(to_account_number)s")
		values.update(range_length=range_length, to_account_number=filters.to_account_number)

	return frappe.db.sql(
		f"""
		SELECT
			gle.company, company.default_currency AS currency,
			gle.account, acc.account_number, acc.account_name,
			gle.cost_center, cc.cost_center_name,
			SUM(CASE WHEN %(has_from_date)s = 1 AND gle.posting_date < %(from_date)s
				AND (%(include_opening_closing)s = 1 OR IFNULL(gle.voucher_type, '') != 'Period Closing Voucher')
				THEN gle.debit - gle.credit ELSE 0 END) AS opening_total,
			SUM(CASE WHEN gle.posting_date >= %(from_date)s AND gle.posting_date <= %(to_date)s
				AND (%(include_period_closing)s = 1 OR IFNULL(gle.voucher_type, '') != 'Period Closing Voucher')
				THEN gle.debit ELSE 0 END) AS debit,
			SUM(CASE WHEN gle.posting_date >= %(from_date)s AND gle.posting_date <= %(to_date)s
				AND (%(include_period_closing)s = 1 OR IFNULL(gle.voucher_type, '') != 'Period Closing Voucher')
				THEN gle.credit ELSE 0 END) AS credit
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		INNER JOIN `tabCost Center` cc ON cc.name = gle.cost_center
		INNER JOIN `tabCompany` company ON company.name = gle.company
		WHERE {' AND '.join(conditions)}
		GROUP BY gle.company, company.default_currency, gle.account, acc.account_number,
			acc.account_name, gle.cost_center, cc.cost_center_name, cc.lft
		ORDER BY gle.company, acc.account_number, gle.account, cc.lft, gle.cost_center
		""",
		values,
		as_dict=True,
	)


def _build_data(rows, show_zero_values=False):
	accounts = {}
	for row in rows:
		debit = flt(row.get("debit"))
		credit = flt(row.get("credit"))
		total = flt(row.get("opening_total")) + debit - credit
		if not show_zero_values and not (debit or credit or total):
			continue
		key = (row.get("company"), row.get("account"))
		group = accounts.setdefault(key, {
			"company": row.get("company"), "currency": row.get("currency"),
			"account": row.get("account"),
			"account_number": row.get("account_number") or row.get("account"),
			"account_name": row.get("account_name") or row.get("account"),
			"debit": 0, "credit": 0, "total": 0, "centers": [],
		})
		group["debit"] += debit
		group["credit"] += credit
		group["total"] += total
		group["centers"].append({
			"cost_center": row.get("cost_center"), "cost_center_name": row.get("cost_center_name"),
			"debit": debit, "credit": credit, "total": total,
		})

	data = []
	for index, group in enumerate(accounts.values(), 1):
		row_id = f"ACCOUNT::{index}::{group['company']}::{group['account']}"
		data.append({
			"row_id": row_id, "parent_row_id": "", "indent": 0, "is_account_row": 1,
			"account_number": group["account_number"], "account_name": group["account_name"],
			"cost_center": "", "debit": group["debit"], "credit": group["credit"],
			"total": group["total"], "currency": group["currency"],
		})
		for center_index, center in enumerate(group["centers"], 1):
			data.append({
				"row_id": f"{row_id}::CC::{center_index}", "parent_row_id": row_id,
				"indent": 1, "is_account_row": 0, "account_number": "", "account_name": "",
				"cost_center": center["cost_center"], "cost_center_name": center["cost_center_name"],
				"debit": center["debit"], "credit": center["credit"], "total": center["total"],
				"currency": group["currency"],
			})
	return data


def _get_summary(data, filters):
	account_rows = [row for row in data if row.get("is_account_row")]
	currencies = {row.get("currency") for row in account_rows if row.get("currency")}
	currency = next(iter(currencies)) if len(currencies) == 1 else None
	values = [
		(sum(flt(row.get("debit")) for row in account_rows), "Blue", _("Total Debit")),
		(sum(flt(row.get("credit")) for row in account_rows), "Red", _("Total Credit")),
		(sum(flt(row.get("total")) for row in account_rows), "Green", _("Total")),
	]
	return [{
		"value": value, "indicator": indicator, "label": label,
		"datatype": "Currency" if currency else "Float", "currency": currency,
	} for value, indicator, label in values]
