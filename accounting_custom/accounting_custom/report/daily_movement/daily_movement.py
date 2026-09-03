import frappe
from frappe import _
from frappe.utils import flt


CURRENCIES = (
	("LBP", "Lebanese Pound Section"),
	("USD", "US Dollar Section"),
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.company or not filters.date:
		return get_columns(), []

	opening_balances = get_balances(filters)
	transactions = get_transactions(filters)
	rows = []
	for currency, section_label in CURRENCIES:
		currency_rows = [row for row in transactions if row.currency == currency]
		incoming = sum(flt(row.incoming) for row in currency_rows)
		outgoing = sum(flt(row.outgoing) for row in currency_rows)
		previous = flt(opening_balances.get(currency))
		current = previous + incoming - outgoing
		rows.append({
			"currency": currency,
			"description": _(section_label),
			"previous_balance": previous,
			"current_balance": current,
			"is_section": 1,
		})
		rows.extend(currency_rows)
		rows.append({
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


def treasury_account_condition(alias="gle", account_alias="account"):
	return f"""(
		{account_alias}.account_type in ('Cash', 'Bank')
		or {alias}.account in (
			select custody.account from `tabCollector Custody Account` custody
		)
		or {alias}.account in (
			select mode_account.default_account
			from `tabMode of Payment Account` mode_account
			where mode_account.company = %(company)s
		)
	)"""


def get_balances(filters):
	rows = frappe.db.sql(
		f"""
		select gle.account_currency currency,
			sum(gle.debit_in_account_currency - gle.credit_in_account_currency) balance
		from `tabGL Entry` gle
		inner join `tabAccount` account on account.name = gle.account
		where gle.company = %(company)s
			and gle.posting_date < %(date)s
			and gle.is_cancelled = 0
			and gle.account_currency in ('LBP', 'USD')
			and {treasury_account_condition()}
		group by gle.account_currency
		""",
		filters,
		as_dict=True,
	)
	return {row.currency: row.balance for row in rows}


def get_transactions(filters):
	rows = frappe.db.sql(
		f"""
		select movement.* from (
			select payment.currency, 'Donation Entry' voucher_type,
				donation.name voucher_no, coalesce(donation.donor_name, donation.donor, '') party,
				coalesce(donation.remarks, '') description,
				sum(payment.donation_amount) incoming, null outgoing,
				donation.creation
			from `tabDonation Entry` donation
			inner join `tabDonation Payment Detail` payment on payment.parent = donation.name
			where donation.company = %(company)s and donation.posting_date = %(date)s
				and donation.docstatus = 1 and payment.currency in ('LBP', 'USD')
			group by donation.name, payment.currency

			union all

			select payment.currency, 'Accounting Payment Entry' voucher_type,
				entry.name voucher_no, coalesce(max(payment.party_name), max(payment.party), '') party,
				coalesce(entry.remarks, '') description,
				null incoming, sum(payment.amount) outgoing,
				entry.creation
			from `tabAccounting Payment Entry` entry
			inner join `tabAccounting Payment Detail` payment on payment.parent = entry.name
			where entry.company = %(company)s and entry.posting_date = %(date)s
				and entry.docstatus = 1 and payment.currency in ('LBP', 'USD')
			group by entry.name, payment.currency

			union all

			select gle.account_currency currency, 'Journal Entry' voucher_type,
				gle.voucher_no, '' party,
				coalesce(max(gle.remarks), 'Currency Exchange') description,
				sum(gle.debit_in_account_currency) incoming,
				sum(gle.credit_in_account_currency) outgoing,
				min(gle.creation) creation
			from `tabGL Entry` gle
			inner join `tabAccount` account on account.name = gle.account
			where gle.company = %(company)s and gle.posting_date = %(date)s
				and gle.is_cancelled = 0 and gle.voucher_type = 'Journal Entry'
				and gle.account_currency in ('LBP', 'USD')
				and {treasury_account_condition()}
				and gle.voucher_no in (
					select exchange.voucher_no
					from `tabGL Entry` exchange
					where exchange.company = %(company)s
						and exchange.posting_date = %(date)s
						and exchange.is_cancelled = 0
						and exchange.voucher_type = 'Journal Entry'
						and exchange.account_currency in ('LBP', 'USD')
					group by exchange.voucher_no
					having count(distinct exchange.account_currency) = 2
				)
			group by gle.voucher_no, gle.account_currency
		) movement
		where coalesce(movement.incoming, 0) > 0 or coalesce(movement.outgoing, 0) > 0
		order by movement.currency, movement.creation, movement.voucher_no
		""",
		filters,
		as_dict=True,
	)
	for row in rows:
		row.incoming = flt(row.incoming) or None
		row.outgoing = flt(row.outgoing) or None
	return rows
