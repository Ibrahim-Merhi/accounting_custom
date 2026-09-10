import frappe
from babel.numbers import get_currency_name, get_currency_symbol
from frappe import _
from frappe.utils import add_days, flt, formatdate


BASE_CURRENCIES = (
	("LBP", "Lebanese Pound Section"),
	("USD", "US Dollar Section"),
)
CURRENCY_LABELS = dict(BASE_CURRENCIES)
BASE_ACCOUNT_NUMBERS = {
	"LBP": ("53000001",),
	"USD": ("53000002",),
}
OTHER_ACCOUNT_NUMBERS = {
	"EUR": ("53000003",),
	"SAR": ("53000004", "53010003"),
	"QAR": ("53000005", "53010002"),
	"KWD": ("53000006",),
	"GBP": ("53000007",),
	"TRY": ("53000008",),
	"CAD": ("53000009",),
	"AUD": ("53000010",),
	"USD": ("53010001",),
}
OTHER_REPORT_SECTIONS = (
	("EUR", "53000003", None, None),
	("SAR", "53000004", None, None),
	("QAR", "53000005", None, None),
	("KWD", "53000006", None, None),
	("GBP", "53000007", None, None),
	("TRY", "53000008", None, None),
	("CAD", "53000009", None, None),
	("AUD", "53000010", None, None),
	("USD", "53010001", "US Dollar External", "الدولار الأمريكي الخارجي"),
	("QAR", "53010002", "Qatari Riyal External", "الريال القطري الخارجي"),
	("SAR", "53010003", "Saudi Riyal External", "الريال السعودي الخارجي"),
)
EXCLUDED_COMPANY = "Namaa"


def execute(filters=None, currency_scope="base"):
	filters = frappe._dict(filters or {})
	if not filters.date:
		return get_columns(), []
	requested_companies = filters.company
	filters.companies = get_selected_companies(requested_companies)
	if requested_companies and not filters.companies:
		return get_columns(), []
	filters.excluded_company = EXCLUDED_COMPANY
	filters.currency_scope = currency_scope

	opening_balances = get_balances(filters)
	transactions = get_transactions(filters)
	if len(filters.companies) == 1:
		for row in transactions:
			row.company = row.company or filters.companies[0]
	companies = list(filters.companies)
	available_companies = {company for company, _currency in opening_balances}
	available_companies.update(row.company for row in transactions if row.company)
	if companies:
		companies.extend(sorted(available_companies.difference(companies)))
	else:
		companies = sorted(available_companies)

	rows = []
	if currency_scope == "other":
		sections = OTHER_REPORT_SECTIONS
	else:
		sections = tuple((code, BASE_ACCOUNT_NUMBERS[code][0], None, None) for code, _label in BASE_CURRENCIES)
	opening_date = formatdate(add_days(filters.date, -1), "dd-MM-yyyy")
	for company in companies:
		rows.append({
			"description": _("Company: {0}").format(company),
			"is_company": 1,
		})
		for currency, account_number, custom_name, custom_name_ar in sections:
			currency_rows = [
				row for row in transactions
				if row.company == company and row.account_number == account_number
			]
			section_key = account_number
			currency_name = custom_name or get_currency_display_name(currency, "en")
			currency_name_ar = custom_name_ar or get_currency_display_name(currency, "ar")
			currency_symbol = get_currency_display_symbol(currency)
			for row in currency_rows:
				row.currency_name = currency_name
				row.currency_name_ar = currency_name_ar
				row.currency_symbol = currency_symbol
				row.section_key = section_key
			incoming = sum(flt(row.incoming) for row in currency_rows)
			outgoing = sum(flt(row.outgoing) for row in currency_rows)
			previous = flt(opening_balances.get((company, account_number)))
			current = previous + incoming - outgoing
			rows.append({
				"company": company,
				"currency": currency,
				"account_number": account_number,
				"section_key": section_key,
				"currency_name": currency_name,
				"currency_name_ar": currency_name_ar,
				"currency_symbol": currency_symbol,
				"description": _(CURRENCY_LABELS.get(currency, currency_name)),
				"previous_balance": previous,
				"current_balance": current,
				"opening_date": opening_date,
				"is_section": 1,
			})
			rows.extend(currency_rows)
			rows.append({
				"company": company,
				"currency": currency,
				"account_number": account_number,
				"section_key": section_key,
				"description": _("Daily Movement Total"),
				"incoming": incoming or None,
				"outgoing": outgoing or None,
				"is_total": 1,
			})
	return get_columns(), rows


def execute_other_currencies(filters=None):
	return execute(filters, currency_scope="other")


def get_currency_display_name(currency, locale):
	try:
		return get_currency_name(currency, locale=locale) or currency
	except (LookupError, TypeError, ValueError):
		return currency


def get_currency_display_symbol(currency):
	if currency == "LBP":
		return "ل.ل"
	try:
		return get_currency_symbol(currency, locale="en") or currency
	except (LookupError, TypeError, ValueError):
		return currency


def get_columns():
	return [
		{"fieldname": "currency", "label": _("Currency"), "fieldtype": "Data", "width": 80},
		{"fieldname": "voucher_type", "label": _("Document Type"), "fieldtype": "Data", "width": 150},
		{"fieldname": "voucher_no", "label": _("Document"), "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 180},
		{"fieldname": "party", "label": _("Party"), "fieldtype": "Data", "width": 190},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 260},
		{"fieldname": "incoming", "label": _("Incoming"), "fieldtype": "Currency", "options": "currency", "width": 130},
		{"fieldname": "outgoing", "label": _("Outgoing"), "fieldtype": "Currency", "options": "currency", "width": 130},
		{"fieldname": "previous_balance", "label": _("Previous Balance"), "fieldtype": "Currency", "options": "currency", "width": 145},
		{"fieldname": "current_balance", "label": _("Current Balance"), "fieldtype": "Currency", "options": "currency", "width": 145},
	]


def get_selected_companies(value):
	if not value:
		return ()
	if isinstance(value, str):
		value = frappe.parse_json(value) if value.lstrip().startswith("[") else [value]
	return tuple(company for company in value if company and company != EXCLUDED_COMPANY)


def company_condition(alias, filters):
	if filters.companies:
		return f"{alias}.company in %(companies)s and {alias}.company != %(excluded_company)s"
	return f"{alias}.company != %(excluded_company)s"


def treasury_account_condition(alias="gle", account_alias="account"):
	return f"""(
		{account_alias}.account_type in ('Cash', 'Bank')
		or {alias}.account in (
			select custody.account from `tabCollector Custody Account` custody
		)
		or {alias}.account in (
			select mode_account.default_account
			from `tabMode of Payment Account` mode_account
			where mode_account.company = {alias}.company
		)
	)"""


def currency_account_condition(alias="gle", account_alias="account", currency_scope="base"):
	account_numbers = (
		OTHER_ACCOUNT_NUMBERS if currency_scope == "other" else BASE_ACCOUNT_NUMBERS
	)
	mapped_accounts = "\n\t\tor ".join(
		f"({alias}.account_currency = '{currency}' and "
		f"{account_alias}.account_number in ({', '.join(repr(number) for number in numbers)}))"
		for currency, numbers in account_numbers.items()
	)
	return f"""(
		{mapped_accounts}
	)"""


def get_balances(filters):
	rows = frappe.db.sql(
		f"""
		select gle.company, account.account_number,
			sum(gle.debit_in_account_currency - gle.credit_in_account_currency) balance
		from `tabGL Entry` gle
		inner join `tabAccount` account on account.name = gle.account
		where {company_condition('gle', filters)}
			and gle.posting_date < %(date)s
			and gle.is_cancelled = 0
			and coalesce(gle.party_type, '') = '' and coalesce(gle.party, '') = ''
			and coalesce(gle.account_currency, '') != ''
			and {currency_account_condition(currency_scope=filters.currency_scope)}
		group by gle.company, account.account_number
		""",
		filters,
		as_dict=True,
	)
	return {(row.company, row.account_number): row.balance for row in rows}


def get_transactions(filters):
	rows = frappe.db.sql(
		f"""
		select movement.* from (
			select gle.company, gle.account_currency currency, account.account_number, 'Journal Entry' voucher_type,
				gle.voucher_no, '' party,
				coalesce(
					max(nullif(line.user_remark, '')),
					trim(replace(max(nullif(gle.remarks, '')), 'Note:', '')),
					''
				) description,
				sum(gle.debit_in_account_currency) incoming,
				sum(gle.credit_in_account_currency) outgoing,
				min(gle.creation) creation, 'Submitted' status
			from `tabGL Entry` gle
			inner join `tabAccount` account on account.name = gle.account
			left join (
				select parent, account, account_currency,
					max(nullif(user_remark, '')) user_remark
				from `tabJournal Entry Account`
				group by parent, account, account_currency
			) line on line.parent = gle.voucher_no
				and line.account = gle.account
				and line.account_currency = gle.account_currency
			where {company_condition('gle', filters)} and gle.posting_date = %(date)s
				and gle.is_cancelled = 0 and gle.voucher_type = 'Journal Entry'
				and coalesce(gle.party_type, '') = '' and coalesce(gle.party, '') = ''
				and coalesce(gle.account_currency, '') != ''
				and {currency_account_condition(currency_scope=filters.currency_scope)}
			group by gle.company, gle.voucher_no, gle.account_currency, account.account_number

			union all

			select journal.company, line.account_currency currency, account.account_number, 'Journal Entry' voucher_type,
				journal.name voucher_no, '' party,
				coalesce(
					max(nullif(line.user_remark, '')),
					trim(replace(max(nullif(journal.user_remark, '')), 'Note:', '')),
					''
				) description,
				sum(line.debit_in_account_currency) incoming,
				sum(line.credit_in_account_currency) outgoing,
				journal.creation, 'Draft' status
			from `tabJournal Entry` journal
			inner join `tabJournal Entry Account` line on line.parent = journal.name
			inner join `tabAccount` account on account.name = line.account
			where {company_condition('journal', filters)} and journal.posting_date = %(date)s
				and journal.docstatus = 0
				and coalesce(line.party_type, '') = '' and coalesce(line.party, '') = ''
				and coalesce(line.account_currency, '') != ''
				and {currency_account_condition('line', currency_scope=filters.currency_scope)}
			group by journal.company, journal.name, line.account_currency, account.account_number
		) movement
		where coalesce(movement.incoming, 0) > 0 or coalesce(movement.outgoing, 0) > 0
		order by movement.company, movement.currency, movement.creation, movement.voucher_no
		""",
		filters,
		as_dict=True,
	)
	for row in rows:
		row.incoming = flt(row.incoming) or None
		row.outgoing = flt(row.outgoing) or None
	return rows
