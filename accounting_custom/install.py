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
	"Custodies": "Receivable",
}


def after_install():
	setup_accounting_customizations()


def after_migrate():
	setup_accounting_customizations()


def setup_accounting_customizations():
	ensure_accounting_roles()
	ensure_party_type_permissions()
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
		elif frappe.db.get_value("Party Type", party_type, "account_type") != account_type:
			frappe.db.set_value("Party Type", party_type, "account_type", account_type)


def ensure_party_type_permissions():
	"""Allow accounting administrators to configure Party Types from Desk."""
	from frappe.permissions import add_permission, update_permission_property

	# ERPNext marks Party Type as setup-only (`in_create`), which suppresses the
	# List View Add button even when a role has create permission. This managed
	# override makes it a normal configurable master for accounting users.
	property_setter = "Party Type-main-in_create"
	if frappe.db.exists("Property Setter", property_setter):
		frappe.db.set_value(
			"Property Setter", property_setter, "value", "0", update_modified=False
		)
	else:
		frappe.make_property_setter({
			"doctype": "Party Type",
			"doctype_or_field": "DocType",
			"property": "in_create",
			"property_type": "Check",
			"value": "0",
		})

	for role in ("System Manager", "Accounts Manager", "Accounts User", "Finance Officer", "Treasurer"):
		filters = {"parent": "Party Type", "role": role, "permlevel": 0, "if_owner": 0}
		if not frappe.db.exists("Custom DocPerm", filters):
			add_permission("Party Type", role, 0, "read")
		permissions = ["read", "write", "create", "report", "export"]
		if role in ("System Manager", "Accounts Manager"):
			permissions.append("delete")
		for permission in permissions:
			update_permission_property(
				"Party Type", role, 0, permission, 1, validate=False
			)
	frappe.clear_cache(doctype="Party Type")


def ensure_accounting_roles():
	for role in (
		"Collector", "Treasurer", "Finance Officer", "Association President",
		"HR Coordinator", "Responsible Manager", "Volunteer", "Public Relations", "CEO",
	):
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
