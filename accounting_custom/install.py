import frappe

from accounting_custom.setup.custom_fields import ensure_custom_fields


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
	ensure_custom_fields()
	ensure_party_types()


def ensure_party_types():
	for party_type, account_type in PARTY_TYPES.items():
		if not frappe.db.exists("DocType", party_type):
			continue
		if not frappe.db.exists("Party Type", party_type):
			frappe.get_doc(
				{"doctype": "Party Type", "party_type": party_type, "account_type": account_type}
			).insert(ignore_permissions=True)
