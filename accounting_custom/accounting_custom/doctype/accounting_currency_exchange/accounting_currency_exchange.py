import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from accounting_custom.accounting.donation_gl import (
	get_account_details,
	get_mode_of_payment_account,
)
from accounting_custom.accounting.standard_exchange_rate import _get_rate


ROUND_OFF_ACCOUNT_NUMBER = "67500002"


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
		if flt(self.to_amount) <= 0:
			frappe.throw(_("Amount To must be greater than zero."))
		self._validate_cost_center(self.from_cost_center, _("Cost Center From"))
		self._validate_cost_center(self.to_cost_center, _("Cost Center To"))

	def _get_payment_account(self, mode_of_payment):
		account = get_mode_of_payment_account(mode_of_payment, self.company)
		details = get_account_details(account, self.company)
		currency = details.account_currency or self.company_currency
		return account, currency

	def _validate_cost_center(self, cost_center, label):
		if not cost_center:
			frappe.throw(_("{0} is required.").format(label))
		if frappe.db.get_value("Cost Center", cost_center, "company") != self.company:
			frappe.throw(_("{0} must belong to company {1}.").format(label, self.company))

	def _journal_exchange_rates(self):
		"""Value both currency legs using the configured company exchange rates."""
		return (
			_get_rate(self.company, self.from_currency, self.company_currency, self.posting_date),
			_get_rate(self.company, self.to_currency, self.company_currency, self.posting_date),
		)

	def _get_round_off_account(self):
		account = frappe.db.get_value(
			"Account",
			{
				"company": self.company,
				"account_number": ROUND_OFF_ACCOUNT_NUMBER,
				"is_group": 0,
			},
			"name",
		)
		if not account:
			frappe.throw(
				_("Round Off account number {0} was not found for company {1}.").format(
					ROUND_OFF_ACCOUNT_NUMBER, self.company
				)
			)
		return account

	def on_submit(self):
		if self.journal_entry:
			frappe.throw(_("A Journal Entry is already linked to this Accounting Currency Exchange."))
		source_rate, target_rate = self._journal_exchange_rates()
		source_base = flt(self.from_amount) * source_rate
		target_base = flt(self.to_amount) * target_rate
		rounding_difference = source_base - target_base
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
			"exchange_rate": target_rate,
			"debit_in_account_currency": self.to_amount,
			"cost_center": self.to_cost_center,
		})
		journal.append("accounts", {
			"account": self.source_account,
			"account_currency": self.from_currency,
			"exchange_rate": source_rate,
			"credit_in_account_currency": self.from_amount,
			"cost_center": self.from_cost_center,
		})
		if abs(rounding_difference) > 0.000000001:
			rounding_row = {
				"account": self._get_round_off_account(),
				"account_currency": self.company_currency,
				"exchange_rate": 1,
				"cost_center": self.to_cost_center,
				"user_remark": _("Currency exchange rounding difference"),
			}
			if rounding_difference > 0:
				rounding_row["debit_in_account_currency"] = rounding_difference
			else:
				rounding_row["credit_in_account_currency"] = abs(rounding_difference)
			journal.append("accounts", rounding_row)
		journal.flags.ignore_company_exchange_rate = True
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


@frappe.whitelist()
def get_mode_of_payment_details(company, mode_of_payment):
	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	account = get_mode_of_payment_account(mode_of_payment, company)
	details = get_account_details(account, company)
	return {"account": account, "currency": details.account_currency or company_currency}
