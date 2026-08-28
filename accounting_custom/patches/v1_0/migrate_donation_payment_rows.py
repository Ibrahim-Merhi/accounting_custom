import frappe
from frappe.utils import flt


def execute():
	if not frappe.db.exists("DocType", "Donation Entry"):
		return
	for name in frappe.get_all("Donation Entry", pluck="name"):
		if frappe.db.exists("Donation Payment Detail", {"parent": name, "parentfield": "payments"}):
			continue
		doc = frappe.get_doc("Donation Entry", name)
		if not flt(doc.donation_amount):
			continue
		if not all((doc.cost_center, doc.mode_of_payment, doc.currency, doc.received_in_account)):
			continue
		row = doc.append(
			"payments",
			{
				"cost_center": doc.cost_center,
				"mode_of_payment": doc.mode_of_payment,
				"currency": doc.currency,
				"donation_amount": doc.donation_amount,
				"received_in_account": doc.received_in_account,
				"exchange_rate": doc.exchange_rate,
				"base_amount": doc.base_donation_amount,
			},
		)
		row.db_insert()
