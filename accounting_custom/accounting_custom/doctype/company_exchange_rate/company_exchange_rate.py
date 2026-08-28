import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class CompanyExchangeRate(Document):
	def validate(self):
		self._validate_required_values()
		self._validate_currency_pair()
		self._validate_rate()
		self._validate_enabled_duplicate()

	def _validate_required_values(self):
		if not self.company:
			frappe.throw(_("Company is required."))
		if not self.from_currency:
			frappe.throw(_("From Currency is required."))
		if not self.to_currency:
			frappe.throw(_("To Currency is required."))
		if not self.effective_date:
			frappe.throw(_("Effective Date is required."))

	def _validate_currency_pair(self):
		if self.from_currency == self.to_currency:
			frappe.throw(_("From Currency and To Currency cannot be the same."))

	def _validate_rate(self):
		if flt(self.exchange_rate) <= 0:
			frappe.throw(_("Exchange Rate must be greater than zero."))

	def _validate_enabled_duplicate(self):
		if not self.enabled:
			return

		duplicate = frappe.db.exists(
			"Company Exchange Rate",
			{
				"company": self.company,
				"from_currency": self.from_currency,
				"to_currency": self.to_currency,
				"effective_date": self.effective_date,
				"enabled": 1,
				"name": ["!=", self.name or ""],
			},
		)

		if duplicate:
			frappe.throw(
				_("An enabled exchange rate already exists for {0}, {1} to {2}, on {3}.").format(
					self.company, self.from_currency, self.to_currency, self.effective_date
				)
			)
