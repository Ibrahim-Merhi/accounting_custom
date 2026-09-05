import frappe
from frappe import _
from frappe.utils import flt


def create_linked_journal_entry(source_doc, gl_rows):
	if source_doc.journal_entry:
		frappe.throw(_("A Journal Entry is already linked to {0}.").format(source_doc.name))

	journal = frappe.get_doc({
		"doctype": "Journal Entry",
		"voucher_type": "Journal Entry",
		"company": source_doc.company,
		"posting_date": source_doc.posting_date,
		"multi_currency": 1,
		"user_remark": source_doc.remarks or _("Created from {0} {1}").format(
			source_doc.doctype, source_doc.name
		),
	})
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
		})

	journal.flags.ignore_company_exchange_rate = True
	journal.flags.ignore_permissions = True
	journal.insert()
	journal.submit()
	source_doc.db_set("journal_entry", journal.name, update_modified=False)
	return journal.name


def cancel_linked_journal_entry(source_doc):
	if not source_doc.journal_entry:
		return
	journal = frappe.get_doc("Journal Entry", source_doc.journal_entry)
	if journal.docstatus == 1:
		journal.flags.ignore_permissions = True
		# The submitted source document links to this Journal Entry. Allow the
		# generated entry to be cancelled as part of cancelling that source.
		journal.ignore_linked_doctypes = (source_doc.doctype,)
		journal.cancel()
