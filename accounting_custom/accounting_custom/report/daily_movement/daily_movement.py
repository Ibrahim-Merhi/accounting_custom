import frappe
from frappe import _
from frappe.utils import flt


CURRENCIES = (
	("LBP", "Lebanese Pound Section"),
	("USD", "US Dollar Section"),
)
EXCLUDED_COMPANY = "Namaa"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.date:
		return get_columns(), []
	requested_companies = filters.company
	filters.companies = get_selected_companies(requested_companies)
	if requested_companies and not filters.companies:
		return get_columns(), []
	filters.excluded_company = EXCLUDED_COMPANY

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
	for company in companies:
		rows.append({
			"description": _("Company: {0}").format(company),
			"is_company": 1,
		})
		for currency, section_label in CURRENCIES:
			currency_rows = [
				row for row in transactions
				if row.company == company and row.currency == currency
			]
			incoming = sum(flt(row.incoming) for row in currency_rows)
			outgoing = sum(flt(row.outgoing) for row in currency_rows)
			previous = flt(opening_balances.get((company, currency)))
			current = previous + incoming - outgoing
			rows.append({
				"company": company,
				"currency": currency,
				"description": _(section_label),
				"previous_balance": previous,
				"current_balance": current,
				"is_section": 1,
			})
			rows.extend(currency_rows)
			rows.append({
				"company": company,
				"currency": currency,
				"description": _("Daily Movement Total"),
				"incoming": incoming or None,
				"outgoing": outgoing or None,
				"is_total": 1,
			})
	return get_columns(), rows


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


def get_balances(filters):
	rows = frappe.db.sql(
		f"""
		select gle.company, gle.account_currency currency,
			sum(gle.debit_in_account_currency - gle.credit_in_account_currency) balance
		from `tabGL Entry` gle
		inner join `tabAccount` account on account.name = gle.account
		where {company_condition('gle', filters)}
			and gle.posting_date < %(date)s
			and gle.is_cancelled = 0
			and gle.account_currency in ('LBP', 'USD')
			and {treasury_account_condition()}
		group by gle.company, gle.account_currency
		""",
		filters,
		as_dict=True,
	)
	return {(row.company, row.currency): row.balance for row in rows}


def get_transactions(filters):
	rows = frappe.db.sql(
		f"""
		select movement.* from (
			select donation.company, payment.currency, 'Donation Entry' voucher_type,
				donation.name voucher_no, coalesce(donation.donor_name, donation.donor, '') party,
				coalesce(donation.remarks, '') description,
				sum(payment.donation_amount) incoming, null outgoing,
				donation.creation, case donation.docstatus when 0 then 'Draft' else 'Submitted' end status
			from `tabDonation Entry` donation
			inner join `tabDonation Payment Detail` payment on payment.parent = donation.name
			where {company_condition('donation', filters)} and donation.posting_date = %(date)s
				and donation.docstatus < 2 and payment.currency in ('LBP', 'USD')
			group by donation.company, donation.name, payment.currency

			union all

			select entry.company, payment.currency, 'Accounting Payment Entry' voucher_type,
				entry.name voucher_no, coalesce(max(payment.party_name), max(payment.party), '') party,
				coalesce(entry.remarks, '') description,
				null incoming, sum(payment.amount) outgoing,
				entry.creation, case entry.docstatus when 0 then 'Draft' else 'Submitted' end status
			from `tabAccounting Payment Entry` entry
			inner join `tabAccounting Payment Detail` payment on payment.parent = entry.name
			where {company_condition('entry', filters)} and entry.posting_date = %(date)s
				and entry.docstatus < 2 and payment.parenttype = 'Accounting Payment Entry'
				and payment.currency in ('LBP', 'USD')
			group by entry.company, entry.name, payment.currency

			union all

			select entry.company, receipt.currency, 'Accounting Receipt Entry' voucher_type,
				entry.name voucher_no, coalesce(max(receipt.party_name), max(receipt.party), '') party,
				coalesce(entry.remarks, '') description,
				sum(receipt.amount) incoming, null outgoing,
				entry.creation, case entry.docstatus when 0 then 'Draft' else 'Submitted' end status
			from `tabAccounting Receipt Entry` entry
			inner join `tabAccounting Payment Detail` receipt on receipt.parent = entry.name
			where {company_condition('entry', filters)} and entry.posting_date = %(date)s
				and entry.docstatus < 2 and receipt.parenttype = 'Accounting Receipt Entry'
				and receipt.currency in ('LBP', 'USD')
			group by entry.company, entry.name, receipt.currency

			union all

			select gle.company, gle.account_currency currency, 'Journal Entry' voucher_type,
				gle.voucher_no, '' party,
				coalesce(max(gle.remarks), 'Currency Exchange') description,
				sum(gle.debit_in_account_currency) incoming,
				sum(gle.credit_in_account_currency) outgoing,
				min(gle.creation) creation, 'Submitted' status
			from `tabGL Entry` gle
			inner join `tabAccount` account on account.name = gle.account
			where {company_condition('gle', filters)} and gle.posting_date = %(date)s
				and gle.is_cancelled = 0 and gle.voucher_type = 'Journal Entry'
				and gle.account_currency in ('LBP', 'USD')
				and {treasury_account_condition()}
			group by gle.company, gle.voucher_no, gle.account_currency

			union all

			select journal.company, line.account_currency currency, 'Journal Entry' voucher_type,
				journal.name voucher_no, '' party,
				coalesce(journal.user_remark, 'Journal Entry') description,
				sum(line.debit_in_account_currency) incoming,
				sum(line.credit_in_account_currency) outgoing,
				journal.creation, 'Draft' status
			from `tabJournal Entry` journal
			inner join `tabJournal Entry Account` line on line.parent = journal.name
			inner join `tabAccount` account on account.name = line.account
			where {company_condition('journal', filters)} and journal.posting_date = %(date)s
				and journal.docstatus = 0 and line.account_currency in ('LBP', 'USD')
				and (
					account.account_type in ('Cash', 'Bank')
					or line.account in (select custody.account from `tabCollector Custody Account` custody)
					or line.account in (
						select mode_account.default_account
						from `tabMode of Payment Account` mode_account
						where mode_account.company = journal.company
					)
				)
			group by journal.company, journal.name, line.account_currency
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
