import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController

from accounting_custom.accounting.branch import validate_journal_entry_branch
from accounting_custom.accounting.donation_gl import get_account_details
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
		validate_journal_entry_branch(self)
		if not self.accounts:
			frappe.throw(_("Add at least two Accounting Rows."))
		for row in self.accounts:
			self.validate_row(row)
		self.total_debit = sum(flt(row.base_debit) for row in self.accounts)
		self.total_credit = sum(flt(row.base_credit) for row in self.accounts)
		if abs(self.total_debit - self.total_credit) > 0.001:
			frappe.throw(_("Total Debit must equal Total Credit."))
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
		cost_center_company = frappe.db.get_value("Cost Center", row.cost_center, "company")
		if cost_center_company != self.company:
			frappe.throw(_("Row {0}: Cost Center does not belong to the selected company.").format(row.idx))
		if flt(row.debit) < 0 or flt(row.credit) < 0 or bool(flt(row.debit)) == bool(flt(row.credit)):
			frappe.throw(_("Row {0}: Enter either Debit or Credit, but not both.").format(row.idx))
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
		row.base_debit = flt(row.debit) * row.exchange_rate
		row.base_credit = flt(row.credit) * row.exchange_rate

	def get_gl_entries(self):
		entries = []
		for row in self.accounts:
			opposite_accounts = [
				other.account for other in self.accounts
				if (flt(row.debit) and flt(other.credit)) or (flt(row.credit) and flt(other.debit))
			]
			account_currency = frappe.get_cached_value("Account", row.account, "account_currency") or self.custom_company_currency
			if account_currency not in (row.currency, self.custom_company_currency):
				frappe.throw(_("Row {0}: Account currency does not match row or company currency.").format(row.idx))
			account_debit = flt(row.debit) if account_currency == row.currency else flt(row.base_debit)
			account_credit = flt(row.credit) if account_currency == row.currency else flt(row.base_credit)
			entries.append(
				frappe._dict(
					posting_date=self.posting_date, company=self.company, account=row.account,
					account_currency=account_currency, debit=flt(row.base_debit), credit=flt(row.base_credit),
					debit_in_account_currency=account_debit, credit_in_account_currency=account_credit,
					voucher_type=self.doctype, voucher_no=self.name, cost_center=row.cost_center,
					against=", ".join(dict.fromkeys(opposite_accounts)),
					party_type=row.party_type or None, party=row.party or None, remarks=self.remarks,
					custom_branch=self.custom_branch, is_opening="No",
				)
			)
		return entries
