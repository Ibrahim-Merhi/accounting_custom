from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from erpnext.controllers.accounts_controller import AccountsController

from accounting_custom.accounting.branch import validate_accounting_payment_branch
from accounting_custom.accounting.donation_gl import (
	get_account_details,
	get_mode_of_payment_account,
	get_mode_of_payment_currency,
)
from accounting_custom.accounting.donor_accounts import get_donor_account
from accounting_custom.accounting.journal_posting import (
	cancel_linked_journal_entry,
	delete_linked_draft_journal_entry,
	submit_linked_journal_entry,
	sync_linked_draft_journal_entry,
)
from accounting_custom.api.exchange_rate import get_company_exchange_rate


class MultiDonation(AccountsController):
	def _reset_amendment_state(self):
		if self.docstatus != 0 or not self.amended_from or not self.is_new():
			return
		self.approval_status = "Draft"
		self.approved_by = None
		self.approved_on = None
		self.journal_entry = None

	def _validate_links(self):
		self._reset_amendment_state()
		super()._validate_links()

	def before_validate(self):
		self._reset_amendment_state()

	def validate(self):
		if getattr(self, "_action", None) == "update_after_submit":
			return
		self._set_company_currency()
		validate_accounting_payment_branch(self)
		self._validate_header()
		self._set_row_values()
		self._set_totals()
		self._validate_company_links()

	def before_submit(self):
		if self.approval_status != "Approved":
			frappe.throw(_("Finance approval is required before submitting this multi donation."))
		self.validate()

	def on_update(self):
		if self.docstatus == 0:
			sync_linked_draft_journal_entry(self, build_gl_entries(self))

	def on_submit(self):
		submit_linked_journal_entry(self, build_gl_entries(self))

	def before_cancel(self):
		cancel_linked_journal_entry(self)

	def on_trash(self):
		delete_linked_draft_journal_entry(self)
		super().on_trash()

	def _set_company_currency(self):
		if self.company:
			self.custom_company_currency = frappe.get_cached_value(
				"Company", self.company, "default_currency"
			)
		if self.company and not self.custom_company_currency:
			frappe.throw(_("Default Currency is not configured for company {0}.").format(self.company))

	def _validate_header(self):
		for fieldname, label in (
			("company", _("Company")),
			("posting_date", _("Date")),
			("custom_branch", _("Branch")),
			("cost_center", _("Cost Center")),
			("donor_account", _("Donor Account")),
			("received_in_account", _("Received In Account")),
		):
			if not self.get(fieldname):
				frappe.throw(_("{0} is required.").format(label))
		if not self.donations:
			frappe.throw(_("Add at least one donation row."))

	def _set_row_values(self):
		for row in self.donations:
			if not row.donor:
				frappe.throw(_("Row {0}: Donor is required.").format(row.idx))
			if not row.mode_of_payment:
				frappe.throw(_("Row {0}: Mode of Payment is required.").format(row.idx))
			if flt(row.donation_amount) <= 0:
				frappe.throw(_("Row {0}: Donation Amount must be greater than zero.").format(row.idx))
			row.donor_account = get_donor_account(row.donor, self.company)
			if row.donor_account != self.donor_account:
				frappe.throw(
					_("Row {0}: donor {1} is configured with account {2}, not {3}.").format(
						row.idx, row.donor, row.donor_account, self.donor_account
					)
				)
			row.currency = get_mode_of_payment_currency(row.mode_of_payment, self.company)
			rate = get_company_exchange_rate(
				self.company, row.currency, self.custom_company_currency, self.posting_date
			)
			row.exchange_rate = flt(rate["exchange_rate"])
			row.base_amount = flt(row.donation_amount) * row.exchange_rate

	def _set_totals(self):
		currency_totals = {}
		for row in self.donations:
			currency_totals[row.currency] = currency_totals.get(row.currency, 0) + flt(row.donation_amount)
		self.total_usd = currency_totals.get("USD", 0)
		self.total_lbp = currency_totals.get("LBP", 0)
		self.base_donation_amount = sum(flt(row.base_amount) for row in self.donations)

	def _validate_company_links(self):
		get_account_details(self.donor_account, self.company)
		get_account_details(self.received_in_account, self.company)
		for doctype, name in (("Branch", self.custom_branch), ("Cost Center", self.cost_center)):
			company_field = "custom_company" if doctype == "Branch" else "company"
			if frappe.db.get_value(doctype, name, company_field) != self.company:
				frappe.throw(_("{0} {1} does not belong to company {2}.").format(doctype, name, self.company))
		for row in self.donations:
			get_account_details(get_mode_of_payment_account(row.mode_of_payment, self.company), self.company)


def _account_amount(details, row, company_currency):
	account_currency = details.account_currency or company_currency
	if account_currency == row.currency:
		return account_currency, flt(row.donation_amount)
	if account_currency == company_currency:
		return account_currency, flt(row.base_amount)
	frappe.throw(
		_("Row {0}: account currency must be {1} or {2}.").format(
			row.idx, row.currency, company_currency
		)
	)


def build_gl_entries(doc):
	"""Build consolidated receipt rows plus donor-by-donor audit rows."""
	collection_rows = OrderedDict()
	income_rows = OrderedDict()
	donor_rows = []
	donor_details = get_account_details(doc.donor_account, doc.company)
	income_details = get_account_details(doc.received_in_account, doc.company)
	remarks = doc.remarks or _("Multi donation receipt")

	def common():
		return {
			"posting_date": doc.posting_date,
			"company": doc.company,
			"voucher_type": doc.doctype,
			"voucher_no": doc.name,
			"cost_center": doc.cost_center,
			"custom_branch": doc.custom_branch,
			"is_opening": "No",
			"remarks": remarks,
		}

	def add_group(groups, key, account, details, base_amount, account_amount, debit):
		if key not in groups:
			row = frappe._dict(common())
			row.update(
				account=account,
				account_currency=details.account_currency or doc.custom_company_currency,
				transaction_currency=details.account_currency or doc.custom_company_currency,
				debit=0,
				credit=0,
				debit_in_account_currency=0,
				credit_in_account_currency=0,
				debit_in_transaction_currency=0,
				credit_in_transaction_currency=0,
			)
			groups[key] = row
		row = groups[key]
		base_field = "debit" if debit else "credit"
		account_field = "debit_in_account_currency" if debit else "credit_in_account_currency"
		transaction_field = "debit_in_transaction_currency" if debit else "credit_in_transaction_currency"
		row[base_field] += base_amount
		row[account_field] += account_amount
		row[transaction_field] += account_amount

	for item in doc.donations:
		collection_account = get_mode_of_payment_account(item.mode_of_payment, doc.company)
		collection_details = get_account_details(collection_account, doc.company)
		collection_currency, collection_amount = _account_amount(
			collection_details, item, doc.custom_company_currency
		)
		income_currency, income_amount = _account_amount(income_details, item, doc.custom_company_currency)
		add_group(
			collection_rows, (collection_account, collection_currency), collection_account,
			collection_details, flt(item.base_amount), collection_amount, True,
		)
		add_group(
			income_rows, (doc.received_in_account, income_currency), doc.received_in_account,
			income_details, flt(item.base_amount), income_amount, False,
		)

		donor_currency, donor_amount = _account_amount(donor_details, item, doc.custom_company_currency)
		for debit in (True, False):
			row = frappe._dict(common())
			row.update(
				account=doc.donor_account,
				account_currency=donor_currency,
				transaction_currency=donor_currency,
				debit=flt(item.base_amount) if debit else 0,
				credit=0 if debit else flt(item.base_amount),
				debit_in_account_currency=donor_amount if debit else 0,
				credit_in_account_currency=0 if debit else donor_amount,
				debit_in_transaction_currency=donor_amount if debit else 0,
				credit_in_transaction_currency=0 if debit else donor_amount,
				party_type="Donor",
				party=item.donor,
				against=doc.donor_account,
				remarks=_("Donor activity - {0}").format(remarks),
			)
			donor_rows.append(row)

	return [*collection_rows.values(), *income_rows.values(), *donor_rows]


@frappe.whitelist()
def set_approval_status(name, action, notes=None):
	doc = frappe.get_doc("Multi Donation", name)
	if doc.docstatus != 0:
		frappe.throw(_("Only draft multi donations can be reviewed."))
	roles = set(frappe.get_roles())
	if action == "Submit for Finance Approval":
		if not ({"Accounts User", "Accounts Manager", "Finance Officer", "Treasurer", "System Manager"} & roles):
			frappe.throw(_("You are not permitted to submit this document for approval."))
		if doc.approval_status not in ("Draft", "Returned"):
			frappe.throw(_("This document is already in review."))
		doc.approval_status = "Pending Finance Approval"
	elif action in ("Approve", "Return", "Reject"):
		if not ({"Finance Officer", "Accounts Manager", "Treasurer", "System Manager"} & roles):
			frappe.throw(_("Only Finance can review this document."))
		if doc.approval_status != "Pending Finance Approval":
			frappe.throw(_("This document is not awaiting Finance approval."))
		doc.approval_status = {"Approve": "Approved", "Return": "Returned", "Reject": "Rejected"}[action]
		doc.approved_by = frappe.session.user if action == "Approve" else None
		doc.approved_on = now_datetime() if action == "Approve" else None
	else:
		frappe.throw(_("Invalid approval action."))
	if notes is not None:
		doc.finance_notes = notes
	doc.save(ignore_permissions=True)
	return doc.approval_status
