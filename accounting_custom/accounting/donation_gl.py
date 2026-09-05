import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries


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


def get_mode_of_payment_currency(mode_of_payment, company):
	account = get_mode_of_payment_account(mode_of_payment, company)
	details = get_account_details(account, company)
	return details.account_currency or frappe.get_cached_value("Company", company, "default_currency")


def get_account_details(account, company):
	details = frappe.db.get_value(
		"Account",
		account,
		["company", "account_currency", "account_type", "is_group", "disabled"],
		as_dict=True,
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


def build_gl_entries(doc):
	entries = []
	remarks = doc.remarks or _("Donation received from {0}").format(doc.donor)
	donor_details = get_account_details(doc.donor_account, doc.company)

	for payment in doc.payments:
		mode_account = get_mode_of_payment_account(payment.mode_of_payment, doc.company)
		collection_account = mode_account
		collector = getattr(doc, "collector", None)
		if collector:
			collection_account = frappe.db.get_value(
				"Collector Custody Account",
				{"parent": collector, "parenttype": "Collector Profile", "currency": payment.currency},
				"account",
			)
			if not collection_account:
				frappe.throw(_("Collector {0} has no custody account for {1}.").format(collector, payment.currency))
		accounts = {
			collection_account: get_account_details(collection_account, doc.company),
			payment.received_in_account: get_account_details(payment.received_in_account, doc.company),
			doc.donor_account: donor_details,
		}
		base_amount = flt(payment.base_amount)
		common = {
			"posting_date": doc.posting_date,
			"company": doc.company,
			"voucher_type": doc.doctype,
			"voucher_no": doc.name,
			"cost_center": payment.cost_center,
			"project": doc.project,
			"custom_branch": getattr(doc, "custom_branch", None),
			"is_opening": "No",
		}

		def entry(account, debit=0, credit=0, against=None, donor_history=False, donor_party=False):
			account_currency = accounts[account].account_currency or doc.custom_company_currency
			if account_currency == payment.currency:
				account_amount = flt(payment.donation_amount)
			elif account_currency == doc.custom_company_currency:
				account_amount = base_amount
			else:
				frappe.throw(
					_("Row {0}: Account {1} currency must be {2} or {3}.").format(
						payment.idx, account, payment.currency, doc.custom_company_currency
					)
				)
			row = frappe._dict(common)
			row.update(
				account=account,
				account_currency=account_currency,
				transaction_currency=account_currency,
				debit=debit,
				credit=credit,
				debit_in_account_currency=account_amount if debit else 0,
				credit_in_account_currency=account_amount if credit else 0,
				debit_in_transaction_currency=account_amount if debit else 0,
				credit_in_transaction_currency=account_amount if credit else 0,
				against=against,
				remarks=(_("Donor activity - {0}").format(remarks) if donor_history else remarks),
			)
			if donor_history or (donor_party and accounts[account].account_type == "Receivable"):
				row.update(party_type="Donor", party=doc.donor)
			return row

		entries.extend(
			[
				entry(collection_account, debit=base_amount, against=payment.received_in_account),
				entry(
					payment.received_in_account,
					credit=base_amount,
					against=collection_account,
					donor_party=True,
				),
				entry(doc.donor_account, debit=base_amount, against=doc.donor_account, donor_history=True),
				entry(doc.donor_account, credit=base_amount, against=doc.donor_account, donor_history=True),
			]
		)
	return entries


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
