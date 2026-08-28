import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


@frappe.whitelist()
def get_company_exchange_rate(company, from_currency, to_currency, transaction_date=None):
	_validate_inputs(company, from_currency, to_currency)
	transaction_date = getdate(transaction_date or nowdate())

	if from_currency == to_currency:
		return _response(
			exchange_rate=1,
			rate_date=transaction_date,
			rate_document=None,
			company=company,
			from_currency=from_currency,
			to_currency=to_currency,
			is_inverse=0,
		)

	direct_rate = _find_rate(company, from_currency, to_currency, transaction_date)
	if direct_rate:
		return _rate_response(direct_rate, company, from_currency, to_currency, is_inverse=False)

	inverse_rate = _find_rate(company, to_currency, from_currency, transaction_date)
	if inverse_rate:
		return _rate_response(inverse_rate, company, from_currency, to_currency, is_inverse=True)

	frappe.throw(
		_(
			"No Company Exchange Rate was found for company {0}, currencies {1} to {2}, "
			"on or before {3}."
		).format(company, from_currency, to_currency, transaction_date)
	)


def _validate_inputs(company, from_currency, to_currency):
	if not company:
		frappe.throw(_("Company is required."))
	if not from_currency:
		frappe.throw(_("From Currency is required."))
	if not to_currency:
		frappe.throw(_("To Currency is required."))


def _find_rate(company, from_currency, to_currency, transaction_date):
	rates = frappe.get_all(
		"Company Exchange Rate",
		filters={
			"company": company,
			"from_currency": from_currency,
			"to_currency": to_currency,
			"effective_date": ["<=", transaction_date],
			"enabled": 1,
		},
		fields=["name", "exchange_rate", "effective_date"],
		order_by="effective_date desc, creation desc",
		limit_page_length=1,
	)
	return rates[0] if rates else None


def _rate_response(rate, company, from_currency, to_currency, is_inverse):
	stored_rate = flt(rate.exchange_rate)
	if stored_rate <= 0:
		message = (
			_("The inverse Company Exchange Rate must be greater than zero.")
			if is_inverse
			else _("The Company Exchange Rate must be greater than zero.")
		)
		frappe.throw(message)

	exchange_rate = 1 / stored_rate if is_inverse else stored_rate
	return _response(
		exchange_rate=exchange_rate,
		rate_date=rate.effective_date,
		rate_document=rate.name,
		company=company,
		from_currency=from_currency,
		to_currency=to_currency,
		is_inverse=int(is_inverse),
	)


def _response(**values):
	return values
