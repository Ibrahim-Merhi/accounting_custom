import frappe

from accounting_custom.accounting_custom.doctype.accounting_payment_entry.accounting_payment_entry import (
	backfill_arabic_amounts,
)
from accounting_custom.accounting.cost_center import backfill_arabic_names
from accounting_custom.accounting.branch import backfill_journal_entry_transaction_currency
from accounting_custom.setup.custom_fields import ensure_custom_fields
from accounting_custom.setup.journal_voucher import ensure_journal_voucher_print_format
from accounting_custom.setup.metadata import ensure_visible_metadata
from accounting_custom.setup.print_formats import ensure_arabic_voucher_print_formats
from accounting_custom.setup.workspace import (
	ensure_accounting_workspace_sections,
	remove_standalone_accounting_program_workspace,
)


PARTY_TYPES = {
	"Employee": "Payable",
	"Supplier": "Payable",
	"Institution": "Payable",
	"Beneficiary": "Payable",
}


def after_install():
	setup_accounting_customizations()


def after_migrate():
	setup_accounting_customizations()


def setup_accounting_customizations():
	ensure_accounting_roles()
	ensure_custom_fields()
	backfill_arabic_names()
	ensure_party_types()
	ensure_arabic_voucher_print_formats()
	ensure_journal_voucher_print_format()
	ensure_visible_metadata()
	backfill_arabic_amounts()
	backfill_journal_entry_transaction_currency()
	ensure_accounting_workspace_sections()
	remove_standalone_accounting_program_workspace()


def ensure_party_types():
	for party_type, account_type in PARTY_TYPES.items():
		if not frappe.db.exists("DocType", party_type):
			continue
		if not frappe.db.exists("Party Type", party_type):
			frappe.get_doc(
				{"doctype": "Party Type", "party_type": party_type, "account_type": account_type}
			).insert(ignore_permissions=True)


def ensure_accounting_roles():
	for role in (
		"Collector", "Treasurer", "Finance Officer", "Association President",
		"HR Coordinator", "Responsible Manager", "Volunteer", "Public Relations", "CEO",
	):
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
