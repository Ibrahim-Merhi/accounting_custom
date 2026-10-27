import frappe
from frappe import _

try:
	from relief_management.overrides.journal_entry import ReliefJournalEntry as BaseJournalEntry
except ImportError:
	from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry as BaseJournalEntry


class CustomJournalEntry(BaseJournalEntry):
	"""Preserve standard validation with Employee Advance receivable compatibility."""

	def submit(self):
		# Payroll accounting rebuild already runs as one controlled operation.
		# Avoid ERPNext's nested background queue for journals with over 100 rows,
		# which otherwise leaves the rebuilt document locked before plans refresh.
		if getattr(frappe.flags, "accounting_custom_sync_journal_submit", False):
			# A rolled-back rebuild can leave a lock for the next naming-series
			# value even though no Journal Entry was committed under that name.
			self.unlock()
			return self._submit()
		return super().submit()

	def validate_party(self):
		for row in self.get("accounts"):
			account_type = frappe.get_cached_value("Account", row.account, "account_type")
			if account_type not in ("Receivable", "Payable"):
				continue
			if not (row.party_type and row.party):
				frappe.throw(
					_("Row {0}: Party Type and Party is required for Receivable / Payable account {1}").format(
						row.idx, row.account
					)
				)
			party_account_type = frappe.db.get_value("Party Type", row.party_type, "account_type")
			if party_account_type == account_type or self._is_employee_advance_receivable(row, account_type):
				continue
			frappe.throw(
				_("Row {0}: Account {1} and Party Type {2} have different account types").format(
					row.idx, row.account, row.party_type
				)
			)

	@staticmethod
	def _is_employee_advance_receivable(row, account_type):
		if not (
			account_type == "Receivable"
			and row.party_type == "Employee"
			and row.reference_type == "Employee Advance"
			and row.reference_name
		):
			return False
		advance = frappe.db.get_value(
			"Employee Advance",
			row.reference_name,
			["employee", "advance_account"],
			as_dict=True,
		)
		return bool(advance and advance.employee == row.party and advance.advance_account == row.account)
