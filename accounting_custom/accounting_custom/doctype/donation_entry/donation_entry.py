import frappe
from frappe import _
from frappe.utils import flt

from erpnext.controllers.accounts_controller import AccountsController

from accounting_custom.accounting.donation_gl import (
	cancel_gl_entries,
	get_account_details,
	get_mode_of_payment_account,
	post_gl_entries,
)
from accounting_custom.accounting.donor_accounts import get_donor_account
from accounting_custom.api.exchange_rate import get_company_exchange_rate
from accounting_custom.utils.arabic_amount import arabic_amount_in_words


class DonationEntry(AccountsController):
	def validate(self):
		self.set_custom_company_currency()
		self.validate_positive_amount()
		self.set_exchange_rate_and_base_amount()
		self.set_arabic_amount_in_words()
		self.validate_linked_companies(require_cost_center=False)

	def before_submit(self):
		self.validate_submission_fields()
		self.set_custom_company_currency()
		self.validate_donor_account()
		self.validate_linked_companies(require_cost_center=True)
		self.validate_mode_of_payment_account()
		self.set_exchange_rate_and_base_amount()
		if flt(self.exchange_rate) <= 0 or flt(self.base_donation_amount) <= 0:
			frappe.throw(_("Exchange Rate and Base Donation Amount must be greater than zero."))

	def on_submit(self):
		post_gl_entries(self)

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
		cancel_gl_entries(self)

	def set_custom_company_currency(self):
		if not self.company:
			return
		custom_company_currency = frappe.db.get_value("Company", self.company, "default_currency")
		if not custom_company_currency:
			frappe.throw(_("Default Currency is not configured for company {0}.").format(self.company))
		self.custom_company_currency = custom_company_currency

	def validate_positive_amount(self):
		if self.donation_amount is not None and flt(self.donation_amount) <= 0:
			frappe.throw(_("Donation Amount must be greater than zero."))

	def set_exchange_rate_and_base_amount(self):
		if not all((self.company, self.currency, self.custom_company_currency, self.posting_date)):
			return
		rate = get_company_exchange_rate(
			self.company, self.currency, self.custom_company_currency, self.posting_date
		)
		self.exchange_rate = flt(rate["exchange_rate"])
		self.base_donation_amount = flt(self.donation_amount) * self.exchange_rate

	def set_arabic_amount_in_words(self):
		self.custom_amount_in_words_arabic = arabic_amount_in_words(
			self.donation_amount or 0, self.currency or ""
		)

	def validate_submission_fields(self):
		for fieldname, label in (
			("company", _("Company")), ("donor", _("Donor")), ("cost_center", _("Cost Center")),
			("donor_account", _("Donor Account")), ("received_in_account", _("Received In Account")),
			("mode_of_payment", _("Mode of Payment")), ("currency", _("Currency")),
		):
			if not self.get(fieldname):
				frappe.throw(_("{0} is required before submitting the Donation Entry.").format(label))
		self.validate_positive_amount()

	def validate_donor_account(self):
		configured_account = get_donor_account(self.donor, self.company)
		if configured_account != self.donor_account:
			frappe.throw(_("The Donor Account does not match the account configured for this donor and company."))

	def validate_linked_companies(self, require_cost_center):
		if self.company and self.donor_account:
			get_account_details(self.donor_account, self.company)
		if self.company and self.received_in_account:
			get_account_details(self.received_in_account, self.company)
		if require_cost_center and not self.cost_center:
			frappe.throw(_("Cost Center is mandatory before submitting the Donation Entry."))
		if self.company and self.cost_center:
			self._validate_company_link("Cost Center", self.cost_center)
		if self.company and self.project:
			self._validate_company_link("Project", self.project)

	def _validate_company_link(self, doctype, name):
		company = frappe.db.get_value(doctype, name, "company")
		if company != self.company:
			frappe.throw(_("{0} {1} does not belong to company {2}.").format(doctype, name, self.company))

	def validate_mode_of_payment_account(self):
		account = get_mode_of_payment_account(self.mode_of_payment, self.company)
		get_account_details(account, self.company)
