import frappe
from frappe import _
from frappe.utils import flt

from accounting_custom.accounting.donation_gl import get_account_details, get_mode_of_payment_account
from accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry import (
	AccountingPaymentEntry,
	_set_approval_status,
)


class AccountingReceiptEntry(AccountingPaymentEntry):
	def before_submit(self):
		for row in self.custom_accounting_rows_copy:
			if not row.account:
				frappe.throw(_("Row {0}: {1} is required.").format(row.idx, _("Account")))
			if not row.cost_center:
				frappe.throw(_("Row {0}: {1} is required.").format(row.idx, _("Cost Center")))
		if self.approval_status != "Approved":
			frappe.throw(_("Finance approval is required before submitting this receipt."))

	def get_gl_entries(self):
		entries = []
		for row in self.custom_accounting_rows_copy:
			mode_account = get_mode_of_payment_account(row.mode_of_payment, self.company)
			credit_account = get_account_details(row.account, self.company)
			debit_account = get_account_details(mode_account, self.company)
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
					against=row.account if debit else mode_account,
					party_type=row.party_type if party and row.party_type else None,
					party=row.party if party and row.party else None, remarks=self.remarks,
					custom_branch=self.custom_branch, is_opening="No",
				)

			entries.extend([
				gl_row(mode_account, debit_account, debit=base_amount),
				gl_row(row.account, credit_account, credit=base_amount, party=True),
			])
		return entries


@frappe.whitelist()
def set_approval_status(name, action, notes=None):
	return _set_approval_status("Accounting Receipt Entry", name, action, notes)
