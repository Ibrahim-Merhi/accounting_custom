import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries

from accounting_custom.api.exchange_rate import get_company_exchange_rate


def get_mode_of_payment_account(mode_of_payment, company):
	account = frappe.db.get_value(
		"Mode of Payment Account",
		{"parent": mode_of_payment, "parenttype": "Mode of Payment", "company": company},
		"default_account",
	)
	if not account:
		frappe.throw(
			_("No default account is configured for Mode of Payment {0} under company {1}.").format(
				mode_of_payment, company
			)
		)
	return account


def get_account_details(account, company):
	details = frappe.db.get_value(
		"Account", account, ["company", "account_currency", "is_group", "disabled"], as_dict=True
	)
	if not details:
		frappe.throw(_("Account {0} was not found.").format(account))
	if details.company != company:
		frappe.throw(_("Account {0} does not belong to company {1}.").format(account, company))
	if details.is_group:
		frappe.throw(_("Account {0} is a group account.").format(account))
	if details.disabled:
		frappe.throw(_("Account {0} is disabled.").format(account))
	return details


def get_account_currency_amount(doc, account_currency):
	if account_currency == doc.custom_company_currency:
		return flt(doc.base_donation_amount)
	if account_currency == doc.currency:
		return flt(doc.donation_amount)
	rate = get_company_exchange_rate(
		doc.company, doc.currency, account_currency, doc.posting_date
	)
	return flt(doc.donation_amount) * flt(rate["exchange_rate"])


def build_gl_entries(doc):
	mode_account = get_mode_of_payment_account(doc.mode_of_payment, doc.company)
	accounts = {
		mode_account: get_account_details(mode_account, doc.company),
		doc.received_in_account: get_account_details(doc.received_in_account, doc.company),
		doc.donor_account: get_account_details(doc.donor_account, doc.company),
	}
	base_amount = flt(doc.base_donation_amount)
	remarks = doc.remarks or _("Donation received from {0}").format(doc.donor)
	common = {
		"posting_date": doc.posting_date,
		"company": doc.company,
		"voucher_type": doc.doctype,
		"voucher_no": doc.name,
		"cost_center": doc.cost_center,
		"project": doc.project,
		"is_opening": "No",
	}

	def entry(account, debit=0, credit=0, against=None, donor_history=False):
		account_currency = accounts[account].account_currency or doc.custom_company_currency
		account_amount = get_account_currency_amount(doc, account_currency)
		row = frappe._dict(common)
		row.update(
			account=account,
			account_currency=account_currency,
			debit=debit,
			credit=credit,
			debit_in_account_currency=account_amount if debit else 0,
			credit_in_account_currency=account_amount if credit else 0,
			against=against,
			remarks=(_("Donor activity - {0}").format(remarks) if donor_history else remarks),
		)
		if donor_history:
			row.update(party_type="Donor", party=doc.donor)
		return row

	return [
		entry(mode_account, debit=base_amount, against=doc.received_in_account),
		entry(doc.received_in_account, credit=base_amount, against=mode_account),
		entry(doc.donor_account, debit=base_amount, against=doc.donor_account, donor_history=True),
		entry(doc.donor_account, credit=base_amount, against=doc.donor_account, donor_history=True),
	]


def post_gl_entries(doc):
	if frappe.db.exists(
		"GL Entry", {"voucher_type": doc.doctype, "voucher_no": doc.name, "is_cancelled": 0}
	):
		frappe.throw(_("Active accounting entries already exist for Donation Entry {0}.").format(doc.name))
	make_gl_entries(build_gl_entries(doc), merge_entries=False, update_outstanding="No")


def cancel_gl_entries(doc):
	make_reverse_gl_entries(
		voucher_type=doc.doctype,
		voucher_no=doc.name,
		update_outstanding="No",
	)
