import frappe
from frappe import _
from frappe.utils import cint

from erpnext.accounts.general_ledger import make_reverse_gl_entries

from accounting_custom.accounting.donation_gl import build_gl_entries
from accounting_custom.accounting.journal_posting import create_linked_journal_entry


SOURCE_DOCTYPES = (
	"Donation Entry",
	"Accounting Payment Entry",
	"Accounting Receipt Entry",
)


@frappe.whitelist()
def backfill_linked_journal_entries(dry_run=1, confirm=0, limit=0):
	"""Create linked Journal Entries for legacy submitted accounting documents.

	Legacy direct GL Entries are reversed inside the same savepoint before the
	replacement Journal Entry is submitted. The operation is idempotent because
	documents that already have ``journal_entry`` are always skipped.
	"""
	dry_run = cint(dry_run)
	confirm = cint(confirm)
	limit = cint(limit)
	if not dry_run and not confirm:
		frappe.throw(_("Set confirm=1 to run the Journal Entry backfill."))

	result = {
		"dry_run": bool(dry_run),
		"candidates": {},
		"legacy_gl_documents": {},
		"processed": [],
		"failed": [],
	}
	remaining = limit
	for doctype in SOURCE_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		query_limit = remaining if limit else 0
		names = frappe.get_all(
			doctype,
			filters={"docstatus": 1, "journal_entry": ["is", "not set"]},
			pluck="name",
			limit=query_limit,
			order_by="creation asc",
		)
		result["candidates"][doctype] = len(names)
		legacy_names = [name for name in names if _has_active_legacy_gl(doctype, name)]
		result["legacy_gl_documents"][doctype] = len(legacy_names)
		if dry_run:
			if limit:
				remaining -= len(names)
				if remaining <= 0:
					break
			continue

		for index, name in enumerate(names):
			savepoint = f"journal_backfill_{doctype.replace(' ', '_')}_{index}"
			frappe.db.savepoint(savepoint)
			try:
				doc = frappe.get_doc(doctype, name)
				if doc.docstatus != 1 or doc.get("journal_entry"):
					continue
				gl_rows = _get_gl_rows(doc)
				had_legacy_gl = _has_active_legacy_gl(doctype, name)
				if had_legacy_gl:
					make_reverse_gl_entries(
						voucher_type=doctype,
						voucher_no=name,
						update_outstanding="No",
					)
				journal_entry = create_linked_journal_entry(doc, gl_rows)
				result["processed"].append({
					"doctype": doctype,
					"name": name,
					"journal_entry": journal_entry,
					"legacy_gl_reversed": had_legacy_gl,
				})
			except Exception as exc:
				frappe.db.rollback(save_point=savepoint)
				result["failed"].append({
					"doctype": doctype,
					"name": name,
					"error": str(exc),
				})
		if limit:
			remaining -= len(names)
			if remaining <= 0:
				break

	return result


def _get_gl_rows(doc):
	if doc.doctype == "Donation Entry":
		return build_gl_entries(doc)
	return doc.get_gl_entries()


def _has_active_legacy_gl(doctype, name):
	return bool(frappe.db.exists(
		"GL Entry",
		{"voucher_type": doctype, "voucher_no": name, "is_cancelled": 0},
	))
