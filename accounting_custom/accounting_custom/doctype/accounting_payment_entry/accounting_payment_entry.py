import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController

from accounting_custom.accounting.branch import validate_accounting_payment_branch
from accounting_custom.accounting.donation_gl import (
	get_account_details,
	get_mode_of_payment_account,
	get_mode_of_payment_currency,
)
from accounting_custom.api.exchange_rate import get_company_exchange_rate


PARTY_NAME_FIELDS = {
	"Employee": "employee_name",
	"Supplier": "supplier_name",
	"Institution": "institution_name",
	"Beneficiary": "beneficiary_name",
}


class AccountingPaymentEntry(AccountsController):
	def validate(self):
		self.set_custom_company_currency()
		validate_accounting_payment_branch(self)
		if not self.accounting_rows:
			frappe.throw(_("Add at least one Accounting Row."))
		for row in self.accounting_rows:
			self.validate_row(row)
		self.total_debit = sum(flt(row.base_amount) for row in self.accounting_rows)
		self.total_credit = self.total_debit
		if self.total_debit <= 0:
			frappe.throw(_("Accounting Payment Entry total must be greater than zero."))

	def on_submit(self):
		if frappe.db.exists("GL Entry", {"voucher_type": self.doctype, "voucher_no": self.name, "is_cancelled": 0}):
			frappe.throw(_("Active accounting entries already exist for {0}.").format(self.name))
		make_gl_entries(self.get_gl_entries(), merge_entries=False, update_outstanding="No")

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
		make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name, update_outstanding="No")

	def set_custom_company_currency(self):
		self.custom_company_currency = frappe.db.get_value("Company", self.company, "default_currency")
		if not self.custom_company_currency:
			frappe.throw(_("Company Currency is required."))

	def validate_row(self, row):
		get_account_details(row.account, self.company)
		mode_account = get_mode_of_payment_account(row.mode_of_payment, self.company)
		get_account_details(mode_account, self.company)
		row.currency = get_mode_of_payment_currency(row.mode_of_payment, self.company)
		cost_center_company = frappe.db.get_value("Cost Center", row.cost_center, "company")
		if cost_center_company != self.company:
			frappe.throw(_("Row {0}: Cost Center does not belong to the selected company.").format(row.idx))
		if flt(row.amount) <= 0:
			frappe.throw(_("Row {0}: Amount must be greater than zero.").format(row.idx))
		if row.party_type or row.party:
			if row.party_type not in PARTY_NAME_FIELDS or not row.party:
				frappe.throw(_("Row {0}: Select a valid Party Type and Party.").format(row.idx))
			if not frappe.db.exists(row.party_type, row.party):
				frappe.throw(_("Row {0}: Party does not exist.").format(row.idx))
			if row.party_type in ("Employee", "Beneficiary"):
				party_company = frappe.db.get_value(row.party_type, row.party, "company")
				if party_company != self.company:
					frappe.throw(_("Row {0}: Party does not belong to the selected company.").format(row.idx))
			row.party_name = frappe.db.get_value(row.party_type, row.party, PARTY_NAME_FIELDS[row.party_type]) or row.party
		rate = get_company_exchange_rate(self.company, row.currency, self.custom_company_currency, self.posting_date)
		row.exchange_rate = flt(rate["exchange_rate"])
		row.base_amount = flt(row.amount) * row.exchange_rate

	def get_gl_entries(self):
		entries = []
		for row in self.accounting_rows:
			mode_account = get_mode_of_payment_account(row.mode_of_payment, self.company)
			destination = get_account_details(row.account, self.company)
			source = get_account_details(mode_account, self.company)
			base_amount = flt(row.base_amount)

			def gl_row(account, details, debit=0, credit=0, party=False):
				account_currency = details.account_currency or self.custom_company_currency
				if account_currency == row.currency:
					account_amount = flt(row.amount)
				elif account_currency == self.custom_company_currency:
					account_amount = base_amount
				else:
					frappe.throw(_("Row {0}: Account {1} currency must be {2} or {3}.").format(
						row.idx, account, row.currency, self.custom_company_currency
					))
				return frappe._dict(
					posting_date=self.posting_date, company=self.company, account=account,
					account_currency=account_currency, transaction_currency=account_currency,
					debit=debit, credit=credit,
					debit_in_account_currency=account_amount if debit else 0,
					credit_in_account_currency=account_amount if credit else 0,
					debit_in_transaction_currency=account_amount if debit else 0,
					credit_in_transaction_currency=account_amount if credit else 0,
					voucher_type=self.doctype, voucher_no=self.name, cost_center=row.cost_center,
					against=mode_account if debit else row.account,
					party_type=row.party_type if party and row.party_type else None,
					party=row.party if party and row.party else None, remarks=self.remarks,
					custom_branch=self.custom_branch, is_opening="No",
				)

			entries.extend([
				gl_row(row.account, destination, debit=base_amount, party=True),
				gl_row(mode_account, source, credit=base_amount),
			])
		return entries
