import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from accounting_custom.accounting.donation_gl import (
	get_account_details,
	get_mode_of_payment_account,
)
from accounting_custom.api.exchange_rate import get_company_exchange_rate


class AccountingCurrencyExchange(Document):
	def validate(self):
		self.company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if not self.company_currency:
			frappe.throw(_("Default Currency is not configured for company {0}.").format(self.company))

		self.source_account, self.from_currency = self._get_payment_account(self.from_mode_of_payment)
		self.target_account, self.to_currency = self._get_payment_account(self.to_mode_of_payment)
		if self.source_account == self.target_account:
			frappe.throw(_("Mode of Payment From and Mode of Payment To must use different accounts."))
		if self.from_currency == self.to_currency:
			frappe.throw(_("Currency From and Currency To must be different."))
		if flt(self.from_amount) <= 0:
			frappe.throw(_("Amount From must be greater than zero."))
		self._set_amounts()

	def _get_payment_account(self, mode_of_payment):
		account = get_mode_of_payment_account(mode_of_payment, self.company)
		details = get_account_details(account, self.company)
		currency = details.account_currency or self.company_currency
		return account, currency

	def _set_amounts(self):
		from_base_rate = self._base_rate(self.from_currency)
		to_base_rate = self._base_rate(self.to_currency)
		if from_base_rate <= 0 or to_base_rate <= 0:
			frappe.throw(_("A valid Company Exchange Rate is required for both currencies."))
		self.exchange_rate = from_base_rate / to_base_rate
		self.to_amount = flt(self.from_amount) * self.exchange_rate

	def on_submit(self):
		if self.journal_entry:
			frappe.throw(_("A Journal Entry is already linked to this Accounting Currency Exchange."))
		journal = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"company": self.company,
			"posting_date": self.posting_date,
			"multi_currency": 1,
			"user_remark": self.remarks or _("Accounting Currency Exchange {0}").format(self.name),
		})
		journal.append("accounts", {
			"account": self.target_account,
			"account_currency": self.to_currency,
			"exchange_rate": self._base_rate(self.to_currency),
			"debit_in_account_currency": self.to_amount,
		})
		journal.append("accounts", {
			"account": self.source_account,
			"account_currency": self.from_currency,
			"exchange_rate": self._base_rate(self.from_currency),
			"credit_in_account_currency": self.from_amount,
		})
		journal.flags.ignore_permissions = True
		journal.insert()
		journal.submit()
		self.db_set("journal_entry", journal.name, update_modified=False)

	def before_cancel(self):
		if not self.journal_entry:
			return
		journal = frappe.get_doc("Journal Entry", self.journal_entry)
		if journal.docstatus == 1:
			journal.flags.ignore_permissions = True
			journal.cancel()

	def _base_rate(self, currency):
		return flt(get_company_exchange_rate(
			self.company,
			currency,
			self.company_currency,
			self.posting_date,
		)["exchange_rate"])


@frappe.whitelist()
def get_mode_of_payment_details(company, mode_of_payment):
	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	account = get_mode_of_payment_account(mode_of_payment, company)
	details = get_account_details(account, company)
	return {"account": account, "currency": details.account_currency or company_currency}
