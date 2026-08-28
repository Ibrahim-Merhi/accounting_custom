import frappe
from frappe import _
from frappe.utils import flt

from erpnext.controllers.accounts_controller import AccountsController

from accounting_custom.accounting.donation_gl import (
	cancel_gl_entries,
	get_account_details,
	get_mode_of_payment_currency,
	get_mode_of_payment_account,
	post_gl_entries,
)
from accounting_custom.accounting.donor_accounts import get_donor_account
from accounting_custom.api.exchange_rate import get_company_exchange_rate
from accounting_custom.utils.arabic_amount import arabic_amount_in_words


class DonationEntry(AccountsController):
	def validate(self):
		self.set_custom_company_currency()
		self.validate_header()
		self.set_payment_amounts()
		self.set_totals()
		self.validate_linked_companies()

	def before_submit(self):
		self.validate()
		self.validate_submit_requirements()
		self.validate_donor_account()

	def on_submit(self):
		post_gl_entries(self)

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
		cancel_gl_entries(self)

	def set_custom_company_currency(self):
		if not self.company:
			return
		currency = frappe.db.get_value("Company", self.company, "default_currency")
		if not currency:
			frappe.throw(_("Default Currency is not configured for company {0}.").format(self.company))
		self.custom_company_currency = currency

	def validate_header(self):
		for fieldname, label in (("company", _("Company")), ("donor", _("Donor")), ("donor_account", _("Donor Account"))):
			if not self.get(fieldname):
				frappe.throw(_("{0} is required.").format(label))
		if not self.payments:
			frappe.throw(_("Add at least one Donation Payment row."))

	def set_payment_amounts(self):
		for row in self.payments:
			if not row.mode_of_payment:
				frappe.throw(_("Row {0}: Mode of Payment is required.").format(row.idx))
			row.currency = get_mode_of_payment_currency(row.mode_of_payment, self.company)
			for fieldname, label in (
				("received_in_account", _("Received In Account")),
			):
				if not row.get(fieldname):
					frappe.throw(_("Row {0}: {1} is required.").format(row.idx, label))
			if flt(row.donation_amount) <= 0:
				frappe.throw(_("Row {0}: Donation Amount must be greater than zero.").format(row.idx))
			rate = get_company_exchange_rate(
				self.company, row.currency, self.custom_company_currency, self.posting_date
			)
			row.exchange_rate = flt(rate["exchange_rate"])
			row.base_amount = flt(row.donation_amount) * row.exchange_rate

	def set_totals(self):
		self.base_donation_amount = sum(flt(row.base_amount) for row in self.payments)
		currency_totals = {}
		for row in self.payments:
			currency_totals[row.currency] = currency_totals.get(row.currency, 0) + flt(row.donation_amount)
		self.total_usd = currency_totals.get("USD", 0)
		self.total_lbp = currency_totals.get("LBP", 0)
		self.custom_amount_in_words_arabic = "\n".join(
			arabic_amount_in_words(amount, currency) for currency, amount in currency_totals.items()
		)

	def validate_submit_requirements(self):
		for row in self.payments:
			if not row.cost_center:
				frappe.throw(_("Row {0}: Cost Center is required before submission.").format(row.idx))

	def validate_donor_account(self):
		configured_account = get_donor_account(self.donor, self.company)
		if configured_account != self.donor_account:
			frappe.throw(_("The Donor Account does not match the account configured for this donor and company."))

	def validate_linked_companies(self):
		get_account_details(self.donor_account, self.company)
		if self.project:
			self._validate_company_link("Project", self.project)
		for row in self.payments:
			get_account_details(row.received_in_account, self.company)
			get_account_details(get_mode_of_payment_account(row.mode_of_payment, self.company), self.company)
			if row.cost_center:
				self._validate_company_link("Cost Center", row.cost_center)

	def _validate_company_link(self, doctype, name):
		company = frappe.db.get_value(doctype, name, "company")
		if company != self.company:
			frappe.throw(_("{0} {1} does not belong to company {2}.").format(doctype, name, self.company))


@frappe.whitelist()
def get_payment_currency(mode_of_payment, company):
	return get_mode_of_payment_currency(mode_of_payment, company)
