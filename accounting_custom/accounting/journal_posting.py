import frappe
from frappe import _
from frappe.utils import flt


def _set_journal_values(journal, source_doc, gl_rows):
	journal.company = source_doc.company
	journal.posting_date = source_doc.posting_date
	journal.multi_currency = 1
	journal.user_remark = source_doc.remarks or _("Created from {0} {1}").format(
		source_doc.doctype, source_doc.name
	)
	journal.set("accounts", [])
	for gl_row in gl_rows:
		account_amount = flt(
			gl_row.debit_in_account_currency or gl_row.credit_in_account_currency
		)
		base_amount = flt(gl_row.debit or gl_row.credit)
		journal.append("accounts", {
			"account": gl_row.account,
			"account_currency": gl_row.account_currency,
			"exchange_rate": base_amount / account_amount if account_amount else 1,
			"debit_in_account_currency": flt(gl_row.debit_in_account_currency),
			"credit_in_account_currency": flt(gl_row.credit_in_account_currency),
			"party_type": gl_row.get("party_type"),
			"party": gl_row.get("party"),
			"cost_center": gl_row.get("cost_center"),
			"project": gl_row.get("project"),
			"custom_branch": gl_row.get("custom_branch"),
			"user_remark": gl_row.get("remarks"),
			"reference_no": gl_row.get("reference_no") or source_doc.get("reference_no"),
		})
	journal.flags.ignore_company_exchange_rate = True
	journal.flags.ignore_permissions = True


def create_linked_journal_entry(source_doc, gl_rows, submit=True):
	if source_doc.journal_entry:
		frappe.throw(_("A Journal Entry is already linked to {0}.").format(source_doc.name))

	journal = frappe.get_doc({
		"doctype": "Journal Entry",
		"voucher_type": "Journal Entry",
	})
	_set_journal_values(journal, source_doc, gl_rows)
	journal.insert()
	source_doc.db_set("journal_entry", journal.name, update_modified=False)
	if submit:
		journal.submit()
	return journal.name


def sync_linked_draft_journal_entry(source_doc, gl_rows):
	if source_doc.docstatus != 0:
		return source_doc.journal_entry
	if not source_doc.journal_entry:
		return create_linked_journal_entry(source_doc, gl_rows, submit=False)
	journal = frappe.get_doc("Journal Entry", source_doc.journal_entry)
	if journal.docstatus != 0:
		frappe.throw(_("Linked Journal Entry {0} must be Draft.").format(journal.name))
	_set_journal_values(journal, source_doc, gl_rows)
	journal.save(ignore_permissions=True)
	return journal.name


def submit_linked_journal_entry(source_doc, gl_rows):
	if not source_doc.journal_entry:
		return create_linked_journal_entry(source_doc, gl_rows)
	journal = frappe.get_doc("Journal Entry", source_doc.journal_entry)
	if journal.docstatus != 0:
		frappe.throw(_("Linked Journal Entry {0} must be Draft.").format(journal.name))
	_set_journal_values(journal, source_doc, gl_rows)
	journal.save(ignore_permissions=True)
	journal.submit()
	return journal.name


def delete_linked_draft_journal_entry(source_doc):
	if not source_doc.journal_entry:
		return
	journal = frappe.get_doc("Journal Entry", source_doc.journal_entry)
	if journal.docstatus != 0:
		return
	journal.flags.ignore_links = True
	journal.delete(ignore_permissions=True)


def cancel_linked_journal_entry(source_doc):
	# Ledger records are immutable audit records. ERPNext keeps submitted
	# Payment Ledger Entries after reversal (marked delinked), but its generic
	# backlink check would still block cancellation of the source document.
	# Ignore those ledger doctypes for this cancellation only; do not delete
	# them and let Journal Entry cancellation create the normal reversals.
	source_doc.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
	if not source_doc.journal_entry:
		return
	journal = frappe.get_doc("Journal Entry", source_doc.journal_entry)
	if journal.docstatus == 1:
		journal.flags.ignore_permissions = True
		# The submitted source document links to this Journal Entry. Allow the
		# generated entry to be cancelled as part of cancelling that source.
		journal.ignore_linked_doctypes = (source_doc.doctype,)
		# Frappe checks backlinks again while cancelling. This flag is scoped to
		# this in-memory generated Journal Entry and prevents the source/JV link
		# from creating a cancellation deadlock. Journal Entry's own on_cancel
		# still reverses its accounting ledger entries normally.
		journal.flags.ignore_links = True
		journal.cancel()
