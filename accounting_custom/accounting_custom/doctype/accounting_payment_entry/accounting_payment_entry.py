import frappe
from frappe import _
from frappe.desk.reportview import get_match_cond
from frappe.utils import flt, now_datetime

from erpnext.controllers.accounts_controller import AccountsController

from accounting_custom.accounting.branch import validate_accounting_payment_branch
from accounting_custom.accounting.donation_gl import (
	get_account_details,
	get_mode_of_payment_account,
	get_mode_of_payment_currency,
)
from accounting_custom.api.exchange_rate import get_company_exchange_rate
from accounting_custom.accounting.journal_posting import (
	cancel_linked_journal_entry,
	create_linked_journal_entry,
)
from accounting_custom.utils.arabic_amount import arabic_amount_in_words


PARTY_NAME_FIELDS = {
	"Employee": "employee_name",
	"Supplier": "supplier_name",
	"Institution": "institution_name",
	"Beneficiary": "full_name_ar",
	"Custodies": "custody_name",
}

PARTY_COMPANY_FIELDS = {
	"Employee": "company",
	"Institution": "company",
	"Custodies": "company",
}


class AccountingPaymentEntry(AccountsController):
	def validate(self):
		self.set_custom_company_currency()
		validate_accounting_payment_branch(self)
		if not self.custom_accounting_rows_copy:
			frappe.throw(_("Add at least one Accounting Row."))
		for row in self.custom_accounting_rows_copy:
			self.validate_row(row)
		self.total_debit = sum(flt(row.base_amount) for row in self.custom_accounting_rows_copy)
		self.total_credit = self.total_debit
		self.set_currency_totals()
		self.set_arabic_amount_in_words()
		if self.total_debit <= 0:
			frappe.throw(_("Accounting Payment Entry total must be greater than zero."))

	def set_currency_totals(self):
		totals = {}
		for row in self.custom_accounting_rows_copy:
			if row.currency:
				totals[row.currency] = totals.get(row.currency, 0) + flt(row.amount)
		self.set("currency_totals", [])
		for currency, amount in totals.items():
			self.append("currency_totals", {
				"currency": currency, "total_debit": amount, "total_credit": amount,
			})

	def set_arabic_amount_in_words(self):
		self.custom_amount_in_words_arabic = "\n".join(
			arabic_amount_in_words(row.total_debit, row.currency)
			for row in self.currency_totals
		)

	def on_submit(self):
		create_linked_journal_entry(self, self.get_gl_entries())

	def before_submit(self):
		for row in self.custom_accounting_rows_copy:
			if not row.account:
				frappe.throw(_("Row {0}: {1} is required.").format(row.idx, _("Account")))
			if not row.cost_center:
				frappe.throw(_("Row {0}: {1} is required.").format(row.idx, _("Cost Center")))
		if self.approval_status != "Approved":
			frappe.throw(_("Finance approval is required before submitting this payment."))

	def before_cancel(self):
		cancel_linked_journal_entry(self)

	def set_custom_company_currency(self):
		self.custom_company_currency = frappe.db.get_value("Company", self.company, "default_currency")
		if not self.custom_company_currency:
			frappe.throw(_("Company Currency is required."))

	def validate_row(self, row):
		if row.account:
			account_details = get_account_details(row.account, self.company)
		else:
			account_details = None
		mode_account = get_mode_of_payment_account(row.mode_of_payment, self.company)
		get_account_details(mode_account, self.company)
		row.currency = get_mode_of_payment_currency(row.mode_of_payment, self.company)
		if row.cost_center:
			cost_center_company = frappe.db.get_value("Cost Center", row.cost_center, "company")
			if cost_center_company != self.company:
				frappe.throw(_("Row {0}: Cost Center does not belong to the selected company.").format(row.idx))
		if flt(row.amount) <= 0:
			frappe.throw(_("Row {0}: Amount must be greater than zero.").format(row.idx))
		if row.party_type or row.party:
			if not row.party_type or not row.party:
				frappe.throw(_("Row {0}: Select a valid Party Type and Party.").format(row.idx))
			if not frappe.db.exists("Party Type", row.party_type):
				frappe.throw(_("Row {0}: Party Type {1} is not configured.").format(row.idx, row.party_type))
			if not frappe.db.exists(row.party_type, row.party):
				frappe.throw(_("Row {0}: Party does not exist.").format(row.idx))
			if row.party_type == "Custodies":
				custody_account = frappe.db.get_value("Custodies", row.party, "account")
				if custody_account != row.account:
					frappe.throw(_("Row {0}: Account must match the Receivable Account configured for this custody.").format(row.idx))
			if account_details and account_details.account_type in ("Receivable", "Payable"):
				party_account_type = frappe.db.get_value("Party Type", row.party_type, "account_type")
				if party_account_type != account_details.account_type:
					frappe.throw(_("Row {0}: Account and Party Type must both be {1}.").format(
						row.idx, account_details.account_type
					))
			if row.party_type == "Supplier":
				party_company_exists = frappe.db.exists(
					"Party Account",
					{"parenttype": "Supplier", "parent": row.party, "company": self.company},
				)
				if not party_company_exists:
					frappe.throw(_("Row {0}: Party does not belong to the selected company.").format(row.idx))
			elif row.party_type in PARTY_COMPANY_FIELDS:
				party_company = frappe.db.get_value(
					row.party_type, row.party, PARTY_COMPANY_FIELDS[row.party_type]
				)
				if party_company != self.company:
					frappe.throw(_("Row {0}: Party does not belong to the selected company.").format(row.idx))
			name_field = PARTY_NAME_FIELDS.get(row.party_type)
			if not name_field:
				name_field = frappe.get_cached_value("DocType", row.party_type, "title_field")
			row.party_name = (
				frappe.db.get_value(row.party_type, row.party, name_field) if name_field else row.party
			) or row.party
		rate = get_company_exchange_rate(self.company, row.currency, self.custom_company_currency, self.posting_date)
		row.exchange_rate = flt(rate["exchange_rate"])
		row.base_amount = flt(row.amount) * row.exchange_rate

	def get_gl_entries(self):
		entries = []
		for row in self.custom_accounting_rows_copy:
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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def supplier_by_company_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""
		select distinct `tabSupplier`.name, `tabSupplier`.supplier_name
		from `tabSupplier`
		inner join `tabParty Account` party_account
			on party_account.parent = `tabSupplier`.name
			and party_account.parenttype = 'Supplier'
		where `tabSupplier`.disabled = 0
			and party_account.company = %(company)s
			and (`tabSupplier`.name like %(txt)s or `tabSupplier`.supplier_name like %(txt)s)
			{match_condition}
		order by `tabSupplier`.name
		limit %(page_len)s offset %(start)s
		""".format(match_condition=get_match_cond("Supplier")),
		{
			"company": filters.get("company"),
			"txt": f"%{txt}%",
			"page_len": page_len,
			"start": start,
		},
	)


def backfill_arabic_amounts():
	# During a first app installation, after_install can run before MariaDB has
	# created this app-owned DocType table. after_migrate will run the backfill
	# once schema synchronization has completed.
	if not frappe.db.table_exists("Accounting Payment Entry", cached=False):
		return
	if not frappe.db.has_column("Accounting Payment Entry", "custom_amount_in_words_arabic"):
		return
	for name in frappe.get_all("Accounting Payment Entry", pluck="name"):
		doc = frappe.get_doc("Accounting Payment Entry", name)
		doc.set_arabic_amount_in_words()
		doc.db_set(
			"custom_amount_in_words_arabic",
			doc.custom_amount_in_words_arabic,
			update_modified=False,
		)


@frappe.whitelist()
def set_approval_status(name, action, notes=None):
	return _set_approval_status("Accounting Payment Entry", name, action, notes)


def _set_approval_status(doctype, name, action, notes=None):
	doc = frappe.get_doc(doctype, name)
	if doc.docstatus != 0:
		frappe.throw(_("Only draft payments can be reviewed."))
	roles = set(frappe.get_roles())
	if action == "Submit for Finance Approval":
		if not ({"Accounts User", "Accounts Manager", "Finance Officer", "System Manager"} & roles):
			frappe.throw(_("You cannot submit this payment for approval."))
		if doc.approval_status not in ("Draft", "Returned"):
			frappe.throw(_("This payment is already in review."))
		doc.approval_status = "Pending Finance Approval"
	elif action in ("Approve", "Return", "Reject"):
		if not ({"Finance Officer", "Accounts Manager", "System Manager"} & roles):
			frappe.throw(_("Finance Officer permission is required."))
		if doc.approval_status != "Pending Finance Approval":
			frappe.throw(_("This payment is not awaiting Finance approval."))
		doc.approval_status = {"Approve":"Approved", "Return":"Returned", "Reject":"Rejected"}[action]
		doc.approved_by = frappe.session.user if action == "Approve" else None
		doc.approved_on = now_datetime() if action == "Approve" else None
	else:
		frappe.throw(_("Invalid approval action."))
	if notes is not None:
		doc.finance_notes = notes
	doc.save(ignore_permissions=True)
	return doc.approval_status
