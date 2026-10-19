from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate
from erpnext.accounts.utils import get_fiscal_year


CLASS_FIELD = "custom_liquidity_report_classification"
FLOW_CLASSES = {"Cash Revenue", "Cash Expense", "Fixed Asset Transfer", "Non-cash"}
BALANCE_CLASSES = {
	"Operating Advance", "Internal Cash", "External Cash", "Gold", "Receivable",
	"Payable", "Long-term Advances and Loans", "Fixed Asset",
	"Accumulated Depreciation", "Frozen",
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_validate(filters)
	companies = _companies(filters)
	fiscal_start = min(getdate(get_fiscal_year(filters.from_date, company=company)[1]) for company in companies)
	entries = _get_entries(companies, getdate(filters.to_date))
	_apply_inherited_classifications(entries, companies)
	centers = _get_cost_centers(companies)
	metrics = _calculate_metrics(
		entries, getdate(filters.from_date), getdate(filters.to_date), fiscal_start
	)
	rows = _build_rows(centers, metrics, filters.report_page or "liquidity", bool(filters.groups_only))
	columns = _columns(filters.report_page or "liquidity")
	message = _message(companies, entries)
	chart = None
	summary = _summary(rows, filters.report_page or "liquidity")
	return columns, rows, message, chart, summary


@frappe.whitelist()
def get_print_data(filters=None, report_page="liquidity"):
	"""Return a fresh Arabic print payload; preview edits remain browser-only."""
	filters = frappe._dict(frappe.parse_json(filters) if isinstance(filters, str) else (filters or {}))
	filters.report_page = report_page if report_page in ("liquidity", "movement") else "liquidity"
	filters.groups_only = 0
	columns, rows, _message_html, _chart, summary = execute(filters)
	for row in rows:
		row["cost_center"] = row.get("cost_center_arabic") or row.get("cost_center")
		row["parent_cost_center"] = (
			row.get("parent_cost_center_arabic") or row.get("parent_cost_center")
		)
	if filters.report_page == "liquidity":
		columns = [column for column in columns if column["fieldname"] != "unclassified"]
	return {
		"report_page": filters.report_page,
		"title": (
			"تقرير أرصدة المراكز والسيولة المتوفرة (بالدولار الأميركي)"
			if filters.report_page == "liquidity"
			else "حركة السيولة خلال الفترة حسب المركز (تدفقات نقدية – الطريقة المباشرة)"
		),
		"from_date": str(filters.from_date), "to_date": str(filters.to_date),
		"companies": _companies(filters), "columns": columns, "rows": rows, "summary": summary,
	}


def _validate(filters):
	if not filters.from_date or not filters.to_date:
		frappe.throw(_("From Date and To Date are required."))
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))
	if filters.report_page and filters.report_page not in ("liquidity", "movement", "summary"):
		frappe.throw(_("Invalid report page."))
	if not frappe.get_meta("Account").has_field(CLASS_FIELD):
		frappe.throw(_("Run migrate to install the Liquidity Report Classification field."))


def _companies(filters):
	companies = filters.get("companies") or []
	if isinstance(companies, str):
		companies = frappe.parse_json(companies) if companies.startswith("[") else [companies]
	companies = [company for company in companies if company]
	if not companies:
		companies = frappe.get_all("Company", pluck="name")
	if not companies:
		frappe.throw(_("No companies are available."))
	return companies


def _get_entries(companies, to_date):
	# Balance-sheet classifications require the complete ledger history. Limiting
	# this query to the fiscal year made a newly classified old balance invisible.
	return frappe.db.sql(
		f"""
		select gle.cost_center, gle.account, gle.posting_date, gle.debit, gle.credit,
			a.{CLASS_FIELD} as classification
		from `tabGL Entry` gle
		inner join `tabAccount` a on a.name = gle.account
		where gle.is_cancelled = 0
			and gle.company in %(companies)s
			and gle.posting_date <= %(to_date)s
			and ifnull(gle.cost_center, '') != ''
		""",
		{"companies": tuple(companies), "to_date": to_date},
		as_dict=True,
	)


def _get_cost_centers(companies):
	return frappe.get_all(
		"Cost Center",
		filters={"company": ["in", companies], "disabled": 0},
		fields=[
			"name", "cost_center_name", "parent_cost_center", "is_group", "lft", "rgt",
			"custom_cost_center_name_arabic", "custom_parent_cost_center_arabic",
		],
		order_by="lft asc, name asc",
	)


def _apply_inherited_classifications(entries, companies):
	"""Use a parent Account classification when a leaf Account is not classified."""
	accounts = frappe.get_all(
		"Account",
		filters={"company": ["in", companies]},
		fields=["name", "parent_account", CLASS_FIELD],
	)
	by_name = {account.name: account for account in accounts}
	resolved = {}

	def resolve(name, seen=None):
		if name in resolved: return resolved[name]
		account = by_name.get(name)
		if not account: return None
		classification = account.get(CLASS_FIELD)
		if classification:
			resolved[name] = classification
			return classification
		seen = seen or set()
		if name in seen: return None
		seen.add(name)
		classification = resolve(account.parent_account, seen) if account.parent_account else None
		resolved[name] = classification
		return classification

	for entry in entries:
		if not entry.classification:
			entry.classification = resolve(entry.account)


def _calculate_metrics(entries, from_date, to_date, fiscal_start=None):
	from_date = getdate(from_date)
	to_date = getdate(to_date)
	fiscal_start = getdate(fiscal_start or from_date)
	result = defaultdict(lambda: defaultdict(float))
	for entry in entries:
		classification = entry.classification or "Unclassified"
		debit = flt(entry.debit)
		credit = flt(entry.credit)
		date = getdate(entry.posting_date)
		center = entry.cost_center
		if classification == "Opening Balance" and date < from_date:
			result[center]["opening_balance"] += credit - debit
		elif (
			classification in ("Cash Revenue", "Cash Expense", "Fixed Asset Transfer")
			and fiscal_start <= date < from_date
		):
			sign = credit - debit if classification == "Cash Revenue" else debit - credit
			result[center]["opening_balance"] += sign if classification == "Cash Revenue" else -sign
		if from_date <= date <= to_date:
			if classification == "Cash Revenue": result[center]["revenue"] += credit - debit
			elif classification == "Cash Expense": result[center]["expense"] += debit - credit
			elif classification == "Fixed Asset Transfer": result[center]["asset_purchase"] += debit - credit
			elif classification == "Non-cash": result[center]["non_cash"] += debit - credit
		if classification in BALANCE_CLASSES:
			amount = debit - credit
			result[center][_balance_key(classification, "end")] += amount
			if date < from_date:
				result[center][_balance_key(classification, "start")] += amount
		if classification == "Unclassified" and (debit or credit):
			result[center]["unclassified"] += debit - credit
	return result


def _balance_key(classification, period):
	return {
		"Operating Advance": "operating_advance", "Internal Cash": "internal_cash",
		"External Cash": "external_cash", "Gold": "gold", "Receivable": "receivable",
		"Payable": "payable", "Long-term Advances and Loans": "long_term",
		"Fixed Asset": "fixed_asset", "Accumulated Depreciation": "accumulated_depreciation",
		"Frozen": "frozen",
	}[classification] + "_" + period


def _complete(metric):
	metric = defaultdict(float, metric)
	metric["balance"] = metric["opening_balance"] + metric["revenue"] - metric["expense"] - metric["asset_purchase"]
	metric["balance_after_advances"] = metric["balance"] - metric["operating_advance_end"]
	metric["available_liquidity"] = metric["internal_cash_end"] + metric["external_cash_end"]
	metric["net_fixed_assets"] = metric["fixed_asset_end"] + metric["accumulated_depreciation_end"]
	metric["check"] = metric["balance_after_advances"] - sum(metric[key] for key in (
		"available_liquidity", "gold_end", "receivable_end", "payable_end", "long_term_end"
	))
	metric["opening_liquidity"] = metric["internal_cash_start"] + metric["external_cash_start"]
	metric["gold_change"] = metric["gold_end"] - metric["gold_start"]
	metric["advance_change"] = metric["operating_advance_end"] - metric["operating_advance_start"]
	metric["receivable_change"] = metric["receivable_end"] - metric["receivable_start"]
	metric["payable_change"] = -(
		(metric["payable_end"] + metric["long_term_end"])
		- (metric["payable_start"] + metric["long_term_start"])
	)
	metric["ending_liquidity"] = (
		metric["opening_liquidity"] + metric["revenue"] - metric["expense"]
		- metric["asset_purchase"] - metric["gold_change"] - metric["advance_change"]
		- metric["receivable_change"] + metric["payable_change"]
	)
	metric["balance_liquidity"] = metric["available_liquidity"]
	metric["difference"] = metric["ending_liquidity"] - metric["balance_liquidity"]
	return metric


def _build_rows(centers, direct_metrics, page, groups_only=False):
	groups_only = groups_only or page == "summary"
	by_name = {center.name: center for center in centers}
	children = defaultdict(list)
	for center in centers:
		children[center.parent_cost_center].append(center.name)

	aggregated = {}
	def aggregate(name):
		metric = defaultdict(float, direct_metrics.get(name, {}))
		for child in children.get(name, []):
			for key, value in aggregate(child).items(): metric[key] += value
		aggregated[name] = metric
		return metric

	for center in centers:
		if not center.parent_cost_center or center.parent_cost_center not in by_name:
			aggregate(center.name)

	rows = []
	def append_branch(name, indent=0):
		center = by_name[name]
		if not groups_only or center.is_group:
			rows.append(_row(center, _complete(aggregated.get(name, {})), page, indent))
		for child in children.get(name, []): append_branch(child, indent + 1)

	for center in centers:
		if not center.parent_cost_center or center.parent_cost_center not in by_name:
			append_branch(center.name)
	return rows


def _row(center, metric, page, indent):
	row = {
		"cost_center": center.cost_center_name or center.name,
		"cost_center_arabic": getattr(center, "custom_cost_center_name_arabic", None) or center.cost_center_name or center.name,
		"cost_center_id": center.name,
		"parent_cost_center": center.parent_cost_center,
		"parent_cost_center_arabic": getattr(center, "custom_parent_cost_center_arabic", None) or center.parent_cost_center,
		"indent": indent, "is_group": int(center.is_group),
	}
	if page == "movement":
		keys = ("opening_liquidity", "revenue", "expense", "asset_purchase", "gold_change",
			"advance_change", "receivable_change", "payable_change", "ending_liquidity",
			"balance_liquidity", "difference")
	elif page == "summary":
		keys = (
			"opening_liquidity", "balance_after_advances", "available_liquidity",
			"liquidity_change", "gold_end", "net_obligations", "asset_purchase", "frozen_end",
		)
	else:
		keys = ("opening_balance", "revenue", "expense", "asset_purchase", "balance",
			"operating_advance_end", "balance_after_advances", "internal_cash_end", "external_cash_end",
			"available_liquidity", "gold_end", "receivable_end", "payable_end", "long_term_end",
			"net_fixed_assets", "non_cash", "frozen_end", "check", "unclassified")
	for key in keys: row[key] = flt(metric[key], 2)
	# Used by the dashboard cards even when it is not a visible detail column.
	row["opening_liquidity"] = flt(metric["opening_liquidity"], 2)
	if page == "summary":
		row["liquidity_change"] = flt(metric["available_liquidity"] - metric["opening_liquidity"], 2)
		row["net_obligations"] = flt(
			metric["receivable_end"] + metric["payable_end"] + metric["long_term_end"], 2
		)
	if page == "liquidity" and row["available_liquidity"] < -0.5:
		row["note"] = _("Negative liquidity: spending from other cost centers")
	return row


def _columns(page):
	base = [{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Data", "width": 220}]
	definitions = {
		"liquidity": [
			("opening_balance", "Opening Balance"), ("revenue", "Revenue"), ("expense", "Expenses"),
			("asset_purchase", "Asset Purchases"), ("balance", "Balance"),
			("operating_advance_end", "Operating Advances"), ("balance_after_advances", "Balance After Advances"),
			("internal_cash_end", "Internal Cash"), ("external_cash_end", "External Cash"),
			("available_liquidity", "Available Liquidity"), ("gold_end", "Gold"),
			("receivable_end", "Receivables"), ("payable_end", "Payables and Accruals"),
			("long_term_end", "Long-term Advances and Loans"), ("net_fixed_assets", "Net Fixed Assets (Information)"),
			("non_cash", "Non-cash Items (Information)"), ("frozen_end", "Frozen (Information)"),
			("check", "Check"), ("unclassified", "Unclassified"),
		],
		"movement": [
			("opening_liquidity", "Opening Liquidity"), ("revenue", "Collected Revenue"),
			("expense", "Paid Expenses"), ("asset_purchase", "Asset Purchases"),
			("gold_change", "Change in Gold"), ("advance_change", "Change in Operating Advances"),
			("receivable_change", "Change in Receivables and Long-term Advances"),
			("payable_change", "Change in Payables and Loans"), ("ending_liquidity", "Ending Liquidity"),
			("balance_liquidity", "Liquidity per Trial Balance"), ("difference", "Difference"),
		],
		"summary": [
			("opening_liquidity", "Opening Liquidity"),
			("balance_after_advances", "Balance After Advances"), ("available_liquidity", "Available Liquidity"),
			("liquidity_change", "Liquidity Change"), ("gold_end", "Gold"),
			("net_obligations", "Receivables Payables and Loans (Net)"),
			("asset_purchase", "Asset Purchases"), ("frozen_end", "Frozen"),
		],
	}
	return base + [
		{"fieldname": fieldname, "label": _(label), "fieldtype": "Currency", "width": 125}
		for fieldname, label in definitions[page]
	] + ([{"fieldname": "note", "label": _("Note"), "fieldtype": "Data", "width": 230}] if page == "liquidity" else [])


def _message(companies, entries):
	unclassified = sorted({entry.account for entry in entries if not entry.classification})
	company_text = ", ".join(companies)
	if not unclassified:
		return f'<div style="text-align:center;font-weight:600">{frappe.utils.escape_html(company_text)}</div>'
	preview = ", ".join(unclassified[:10])
	more = len(unclassified) - 10
	if more > 0: preview += _(" and {0} more").format(more)
	return (
		f'<div class="alert alert-warning"><strong>{_("Accounts requiring classification")} ({len(unclassified)}):</strong> '
		f'{frappe.utils.escape_html(preview)}</div>'
	)


def _summary(rows, page):
	groups = [row for row in rows if row.get("indent") == 0]
	if page == "movement":
		return [
			{"value": sum(row["balance_liquidity"] for row in groups), "label": _("Available Liquidity"), "datatype": "Currency", "indicator": "Green"},
			{"value": sum(row["difference"] for row in groups), "label": _("Difference"), "datatype": "Currency", "indicator": "Red"},
		]
	root = lambda key: sum(row.get(key, 0) for row in groups)
	return [
		{"value": sum(row["available_liquidity"] for row in groups), "label": _("Available Liquidity"), "datatype": "Currency", "indicator": "Green"},
		{"value": root("available_liquidity") - root("opening_liquidity"), "label": _("Liquidity Change"), "datatype": "Currency", "indicator": "Blue"},
		{"value": sum(row["gold_end"] for row in groups), "label": _("Gold"), "datatype": "Currency", "indicator": "Blue"},
		{"value": root("asset_purchase"), "label": _("Asset Purchases"), "datatype": "Currency", "indicator": "Orange"},
		{"value": root("frozen_end"), "label": _("Frozen"), "datatype": "Currency", "indicator": "Grey"},
		{"value": sum(1 for row in rows if not row["is_group"] and row.get("available_liquidity", 0) < -0.5), "label": _("Negative Liquidity Centers"), "datatype": "Int", "indicator": "Red"},
	]
