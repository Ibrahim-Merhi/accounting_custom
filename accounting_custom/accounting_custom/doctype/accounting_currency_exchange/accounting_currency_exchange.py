import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from accounting_custom.accounting.donation_gl import (
	get_account_details,
	get_mode_of_payment_account,
)
from accounting_custom.accounting.journal_posting import (
	cancel_linked_journal_entry,
	delete_linked_draft_journal_entry,
	submit_linked_journal_entry,
	sync_linked_draft_journal_entry,
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

	def get_gl_entries(self):
		source_rate, target_rate = self._journal_exchange_rates()
		source_base = flt(self.from_amount) * source_rate
		target_base = flt(self.to_amount) * target_rate
		rounding_difference = source_base - target_base
		entries = [frappe._dict({
			"account": self.target_account,
			"account_currency": self.to_currency,
			"debit": target_base,
			"debit_in_account_currency": self.to_amount,
			"cost_center": self.to_cost_center,
			"remarks": self.remarks,
		}), frappe._dict({
			"account": self.source_account,
			"account_currency": self.from_currency,
			"credit": source_base,
			"credit_in_account_currency": self.from_amount,
			"cost_center": self.from_cost_center,
			"remarks": self.remarks,
		})]
		if abs(rounding_difference) > 0.000000001:
			rounding_row = frappe._dict({
				"account": self._get_round_off_account(),
				"account_currency": self.company_currency,
				"cost_center": self.to_cost_center,
				"remarks": _("Currency exchange rounding difference"),
			})
			if rounding_difference > 0:
				rounding_row.debit = rounding_difference
				rounding_row["debit_in_account_currency"] = rounding_difference
			else:
				rounding_row.credit = abs(rounding_difference)
				rounding_row["credit_in_account_currency"] = abs(rounding_difference)
			entries.append(rounding_row)
		return entries

	def on_update(self):
		if self.docstatus == 0:
			sync_linked_draft_journal_entry(self, self.get_gl_entries())

	def on_submit(self):
		submit_linked_journal_entry(self, self.get_gl_entries())

	def before_cancel(self):
		cancel_linked_journal_entry(self)

	def on_trash(self):
		delete_linked_draft_journal_entry(self)
		super().on_trash()


@frappe.whitelist()
def get_mode_of_payment_details(company, mode_of_payment):
	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	account = get_mode_of_payment_account(mode_of_payment, company)
	details = get_account_details(account, company)
	return {"account": account, "currency": details.account_currency or company_currency}
