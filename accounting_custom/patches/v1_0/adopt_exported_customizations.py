import frappe

from accounting_custom.setup.custom_fields import ensure_donor_account_fields


SERVER_SCRIPTS = {
	"Arabic numbers": ("Donation Entry", "Before Save"),
	"Donation Entry BS": ("Donation Entry", "Before Submit"),
	"Donation Entry AS": ("Donation Entry", "After Submit"),
	"Donation Entry BC": ("Donation Entry", "Before Cancel"),
	"Validate Company Exchange Rate": ("Company Exchange Rate", "Before Save"),
}


def execute():
	ensure_donor_account_fields()
	_remove_adopted_donation_entry_custom_fields()
	_disable_replaced_runtime_scripts()


def _remove_adopted_donation_entry_custom_fields():
	if not frappe.db.exists("DocType", "Donation Entry"):
		return
	standard_fields = {
		row.fieldname
		for row in frappe.get_all("DocField", filters={"parent": "Donation Entry"}, fields=["fieldname"])
	}
	for fieldname in ("custom_hijri_date", "custom_amount_in_words_arabic"):
		custom_field = frappe.db.get_value(
			"Custom Field", {"dt": "Donation Entry", "fieldname": fieldname}, "name"
		)
		if custom_field and fieldname in standard_fields:
			frappe.db.delete("Property Setter", {"doc_type": "Donation Entry", "field_name": fieldname})
			frappe.db.delete("Custom Field", {"name": custom_field})
	frappe.clear_cache(doctype="Donation Entry")


def _disable_replaced_runtime_scripts():
	for name, (reference_doctype, event) in SERVER_SCRIPTS.items():
		row = frappe.db.get_value(
			"Server Script", name, ["reference_doctype", "doctype_event", "disabled"], as_dict=True
		)
		if row and row.reference_doctype == reference_doctype and row.doctype_event == event and not row.disabled:
			frappe.db.set_value("Server Script", name, "disabled", 1, update_modified=False)

	client = frappe.db.get_value("Client Script", "Donor and companies", ["dt", "enabled"], as_dict=True)
	if client and client.dt == "Donation Entry" and client.enabled:
		frappe.db.set_value("Client Script", "Donor and companies", "enabled", 0, update_modified=False)
