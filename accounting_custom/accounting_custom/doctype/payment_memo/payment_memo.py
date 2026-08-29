import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries

from accounting_custom.accounting.donation_gl import get_account_details
from accounting_custom.api.exchange_rate import get_company_exchange_rate


ROUTE = {
	"Pending HR Coordinator": ("HR Coordinator", "Pending Manager"),
	"Pending Manager": ("Responsible Manager", "Pending Finance"),
	"Pending Finance": ("Finance Officer", "Pending President"),
	"Pending President": ("Association President", "Pending Treasurer"),
	"Pending Treasurer": ("Treasurer", "Approved for Payment"),
}


class PaymentMemo(Document):
	def before_insert(self):
		self.requested_by = frappe.session.user

	def validate(self):
		if self.employee:
			self.applicant_name = frappe.db.get_value("Employee", self.employee, "employee_name")
		if self.payment_type == "Salary Advance" and (self.applicant_type != "Employee" or not self.employee):
			frappe.throw(_("Salary Advance requires an Employee applicant."))
		if self.applicant_type != "Treasurer" and not self.responsible_manager:
			frappe.throw(_("Responsible Manager is required."))
		if not self.allocations:
			frappe.throw(_("Add at least one account and cost center allocation."))
		self.total_amount = 0
		for row in self.allocations:
			row.currency = self.currency
			get_account_details(row.account, self.company)
			if frappe.db.get_value("Cost Center", row.cost_center, "company") != self.company:
				frappe.throw(_("Row {0}: Cost Center does not belong to the selected company.").format(row.idx))
			if row.project and frappe.db.get_value("Project", row.project, "company") != self.company:
				frappe.throw(_("Row {0}: Project does not belong to the selected company.").format(row.idx))
			if flt(row.amount) <= 0:
				frappe.throw(_("Row {0}: Amount must be greater than zero.").format(row.idx))
			self.total_amount += flt(row.amount)
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		self.exchange_rate = flt(get_company_exchange_rate(
			self.company, self.currency, company_currency, self.posting_date
		)["exchange_rate"])
		self.base_total_amount = self.total_amount * self.exchange_rate
		if self.payment_account:
			get_account_details(self.payment_account, self.company)
		self.validate_custody_closure()

	def validate_custody_closure(self):
		if self.payment_type != "Custody Closure":
			return
		custody = frappe.db.get_value(
			"Payment Memo", self.settlement_against,
			["payment_type", "docstatus", "company", "currency", "applicant_name"],
			as_dict=True,
		)
		if not custody or custody.payment_type != "Custody" or custody.docstatus != 1:
			frappe.throw(_("Select a submitted Custody Payment Memo to close."))
		if custody.company != self.company or custody.currency != self.currency:
			frappe.throw(_("Custody closure company and currency must match the original custody."))
		custody_accounts = frappe.get_all(
			"Payment Memo Detail", filters={"parent": self.settlement_against}, pluck="account"
		)
		if self.payment_account and self.payment_account not in custody_accounts:
			frappe.throw(_("Custody Closure account must be an allocation account from the original custody."))
		if flt(self.total_amount) > get_custody_outstanding(self.settlement_against, self.name):
			frappe.throw(_("Custody closure exceeds the outstanding custody amount."))

	def before_submit(self):
		if self.approval_status != "Approved for Payment":
			frappe.throw(_("The memo must complete all approvals before payment."))
		if not self.payment_account:
			frappe.throw(_("Payment / Custody Account is required before payment."))

	def on_submit(self):
		self.db_set("approval_status", "Paid")
		make_gl_entries(self.get_gl_entries(), merge_entries=False, update_outstanding="No")
		self.update_custody_status()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
		make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name, update_outstanding="No")
		self.update_custody_status()

	def update_custody_status(self):
		if self.payment_type != "Custody Closure" or not self.settlement_against:
			return
		status = "Closed" if not get_custody_outstanding(self.settlement_against) else "Paid"
		frappe.db.set_value("Payment Memo", self.settlement_against, "approval_status", status)

	def get_gl_entries(self):
		entries = []
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		payment_details = get_account_details(self.payment_account, self.company)
		for row in self.allocations:
			details = get_account_details(row.account, self.company)
			base_amount = flt(row.amount) * flt(self.exchange_rate)
			def account_amount(account_details):
				account_currency = account_details.account_currency or company_currency
				if account_currency == self.currency:
					return account_currency, flt(row.amount)
				if account_currency == company_currency:
					return account_currency, base_amount
				frappe.throw(_("Row {0}: Account currency must be {1} or {2}.").format(
					row.idx, self.currency, company_currency
				))

			debit_currency, debit_amount = account_amount(details)
			credit_currency, credit_amount = account_amount(payment_details)
			common = {
				"posting_date": self.posting_date, "company": self.company,
				"voucher_type": self.doctype, "voucher_no": self.name,
				"cost_center": row.cost_center, "project": row.project or self.project,
				"remarks": row.description or self.payment_type, "is_opening": "No",
			}
			entries.append(frappe._dict(common, account=row.account, debit=base_amount, credit=0,
				account_currency=debit_currency, transaction_currency=debit_currency,
				debit_in_account_currency=debit_amount, debit_in_transaction_currency=debit_amount,
				credit_in_account_currency=0, credit_in_transaction_currency=0,
				against=self.payment_account))
			entries.append(frappe._dict(common, account=self.payment_account, debit=0, credit=base_amount,
				account_currency=credit_currency, transaction_currency=credit_currency,
				credit_in_account_currency=credit_amount, credit_in_transaction_currency=credit_amount,
				debit_in_account_currency=0, debit_in_transaction_currency=0,
				against=row.account))
		return entries


@frappe.whitelist()
def transition(name, action, notes=None):
	doc = frappe.get_doc("Payment Memo", name)
	if doc.docstatus != 0:
		frappe.throw(_("Only draft payment memos can move through approval."))
	roles = set(frappe.get_roles())
	if action == "Submit Request":
		if doc.requested_by != frappe.session.user and "System Manager" not in roles:
			frappe.throw(_("Only the requester can submit this memo for approval."))
		if doc.approval_status not in ("Draft", "Returned"):
			frappe.throw(_("This memo has already been submitted for approval."))
		if doc.applicant_type == "Treasurer":
			next_state = "Pending Finance"
		elif doc.payment_type == "Salary Advance":
			next_state = "Pending HR Coordinator"
		else:
			next_state = "Pending Manager"
	elif action == "Approve":
		if doc.approval_status not in ROUTE:
			frappe.throw(_("This memo is not awaiting approval."))
		required_role, next_state = ROUTE[doc.approval_status]
		if required_role not in roles and "System Manager" not in roles:
			frappe.throw(_("Role {0} is required for this action.").format(required_role))
		if (
			doc.approval_status == "Pending Manager"
			and doc.responsible_manager != frappe.session.user
			and "System Manager" not in roles
		):
			frappe.throw(_("Only the selected Responsible Manager can review this memo."))
		if doc.approval_status == "Pending Finance" and not doc.payment_account:
			frappe.throw(_("Finance must select the Payment / Custody Account."))
		user_field = {"Pending Finance":"finance_officer", "Pending President":"president", "Pending Treasurer":"treasurer"}.get(doc.approval_status)
		if user_field:
			doc.set(user_field, frappe.session.user)
	elif action in ("Return", "Reject"):
		if doc.approval_status not in ROUTE:
			frappe.throw(_("This memo is not awaiting review."))
		required_role = ROUTE[doc.approval_status][0]
		if required_role not in roles and "System Manager" not in roles:
			frappe.throw(_("Role {0} is required for this action.").format(required_role))
		if (
			doc.approval_status == "Pending Manager"
			and doc.responsible_manager != frappe.session.user
			and "System Manager" not in roles
		):
			frappe.throw(_("Only the selected Responsible Manager can review this memo."))
		next_state = "Returned" if action == "Return" else "Rejected"
	else:
		frappe.throw(_("Invalid workflow action."))
	if notes:
		note_field = {
			"Pending Manager":"manager_notes", "Pending Finance":"finance_notes",
			"Pending President":"president_notes", "Pending Treasurer":"treasurer_notes",
		}.get(doc.approval_status)
		if note_field:
			doc.set(note_field, notes)
	doc.approval_status = next_state
	doc.save(ignore_permissions=True)
	return next_state


def get_custody_outstanding(custody_name, exclude_closure=None):
	custody_amount = flt(frappe.db.get_value("Payment Memo", custody_name, "total_amount"))
	conditions = " and name != %(exclude)s" if exclude_closure else ""
	closed_amount = frappe.db.sql(
		f"""select coalesce(sum(total_amount), 0) from `tabPayment Memo`
		where docstatus=1 and payment_type='Custody Closure'
		and settlement_against=%(custody)s {conditions}""",
		{"custody": custody_name, "exclude": exclude_closure},
	)[0][0]
	return custody_amount - flt(closed_amount)


@frappe.whitelist()
def add_ceo_comment(name, comment):
	if not ({"CEO", "System Manager"} & set(frappe.get_roles())):
		frappe.throw(_("CEO role is required."))
	doc = frappe.get_doc("Payment Memo", name)
	doc.db_set("ceo_comment", (comment or "").strip())
	doc.add_comment("Comment", _("CEO: {0}").format((comment or "").strip()))
	return doc.ceo_comment
