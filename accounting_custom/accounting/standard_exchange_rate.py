import frappe
from frappe import _
from frappe.utils import flt

from accounting_custom.api.exchange_rate import get_company_exchange_rate


def apply_journal_entry_exchange_rates(doc, method=None):
	if getattr(doc, "flags", {}).get("ignore_company_exchange_rate"):
		return
	if not doc.company or not doc.posting_date:
		return

	company_currency = _get_company_currency(doc.company)
	transaction_date = doc.posting_date

	for row in doc.accounts or []:
		account_currency = row.account_currency or frappe.get_cached_value(
			"Account", row.account, "account_currency"
		)
		if not account_currency:
			continue

		row.account_currency = account_currency
		row.exchange_rate = _get_rate(
			doc.company, account_currency, company_currency, transaction_date
		)


def apply_payment_entry_exchange_rates(doc, method=None):
	if not doc.company or not doc.posting_date:
		return

	company_currency = _get_company_currency(doc.company)
	transaction_date = doc.posting_date

	if doc.paid_from_account_currency:
		doc.source_exchange_rate = _get_rate(
			doc.company,
			doc.paid_from_account_currency,
			company_currency,
			transaction_date,
		)

	if doc.paid_to_account_currency:
		doc.target_exchange_rate = _get_rate(
			doc.company,
			doc.paid_to_account_currency,
			company_currency,
			transaction_date,
		)


def apply_transaction_exchange_rate(doc, method=None):
	transaction_date = doc.get("posting_date") or doc.get("transaction_date")
	if not doc.company or not doc.currency or not transaction_date:
		return

	company_currency = _get_company_currency(doc.company)
	doc.conversion_rate = _get_rate(
		doc.company, doc.currency, company_currency, transaction_date
	)


def _get_company_currency(company):
	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	if not company_currency:
		frappe.throw(_("Default Currency is not configured for company {0}.").format(company))
	return company_currency


def _get_rate(company, from_currency, to_currency, transaction_date):
	result = get_company_exchange_rate(
		company=company,
		from_currency=from_currency,
		to_currency=to_currency,
		transaction_date=transaction_date,
	)
	rate = flt(result.get("exchange_rate"))
	if rate <= 0:
		frappe.throw(
			_("No valid Company Exchange Rate exists for {0} to {1}.").format(
				from_currency, to_currency
			)
		)
	return rate
