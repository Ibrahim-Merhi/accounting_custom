import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries

from accounting_custom.accounting.donation_gl import get_account_details
from accounting_custom.api.exchange_rate import get_company_exchange_rate


class CollectorHandover(Document):
	def validate(self):
		if not self.lines:
			frappe.throw(_("Add at least one handover line."))
		profile = frappe.db.get_value("Collector Profile", self.collector, ["company", "active"], as_dict=True)
		if not profile or not profile.active or profile.company != self.company:
			frappe.throw(_("Select an active collector for the selected company."))
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		self.total_base_amount = 0
		handover_totals = {}
		for row in self.lines:
			self.validate_line(row)
			key = (row.donation_entry, row.currency)
			handover_totals[key] = handover_totals.get(key, 0) + flt(row.amount)
			rate = get_company_exchange_rate(
				self.company, row.currency, company_currency, self.posting_date
			)["exchange_rate"]
			self.total_base_amount += flt(row.amount) * flt(rate)
		for (donation_entry, currency), amount in handover_totals.items():
			if amount > get_donation_outstanding(donation_entry, currency, self.name):
				frappe.throw(_("Handover total exceeds the outstanding {0} amount for {1}.").format(
					currency, donation_entry
				))

	def validate_line(self, row):
		if flt(row.amount) <= 0:
			frappe.throw(_("Row {0}: Amount must be greater than zero.").format(row.idx))
		donation = frappe.db.get_value(
			"Donation Entry", row.donation_entry, ["collector", "company", "docstatus"], as_dict=True
		)
		if not donation or donation.docstatus != 1 or donation.collector != self.collector or donation.company != self.company:
			frappe.throw(_("Row {0}: Donation is not a submitted donation for this collector.").format(row.idx))
		configured_source = frappe.db.get_value(
			"Collector Custody Account",
			{"parent": self.collector, "parenttype": "Collector Profile", "currency": row.currency},
			"account",
		)
		if row.source_account != configured_source:
			frappe.throw(_("Row {0}: Source must be the collector custody account for {1}.").format(row.idx, row.currency))
		for account in (row.source_account, row.destination_account):
			details = get_account_details(account, self.company)
			if details.account_currency != row.currency:
				frappe.throw(_("Row {0}: Account currency must be {1}.").format(row.idx, row.currency))
		if frappe.db.get_value("Cost Center", row.cost_center, "company") != self.company:
			frappe.throw(_("Row {0}: Cost Center does not belong to the selected company.").format(row.idx))
		if flt(row.amount) > get_donation_outstanding(row.donation_entry, row.currency, self.name):
			frappe.throw(_("Row {0}: Amount exceeds the donation amount still with the collector.").format(row.idx))

	def on_submit(self):
		self.db_set("received_by", frappe.session.user)
		make_gl_entries(self.get_gl_entries(), merge_entries=False, update_outstanding="No")
		self.update_donation_statuses()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
		make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name, update_outstanding="No")
		self.update_donation_statuses()

	def get_gl_entries(self):
		entries = []
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		for row in self.lines:
			rate = flt(get_company_exchange_rate(
				self.company, row.currency, company_currency, self.posting_date
			)["exchange_rate"])
			base_amount = flt(row.amount) * rate
			common = {
				"posting_date": self.posting_date, "company": self.company,
				"voucher_type": self.doctype, "voucher_no": self.name,
				"account_currency": row.currency, "transaction_currency": row.currency,
				"cost_center": row.cost_center, "remarks": self.remarks,
				"is_opening": "No",
			}
			entries.append(frappe._dict(common, account=row.destination_account, debit=base_amount, credit=0,
				debit_in_account_currency=row.amount, debit_in_transaction_currency=row.amount,
				credit_in_account_currency=0, credit_in_transaction_currency=0,
				against=row.source_account))
			entries.append(frappe._dict(common, account=row.source_account, debit=0, credit=base_amount,
				credit_in_account_currency=row.amount, credit_in_transaction_currency=row.amount,
				debit_in_account_currency=0, debit_in_transaction_currency=0,
				against=row.destination_account))
		return entries

	def update_donation_statuses(self):
		for donation_entry in {row.donation_entry for row in self.lines}:
			currencies = frappe.get_all(
				"Donation Payment Detail", filters={"parent": donation_entry},
				fields=["distinct currency as currency"],
			)
			outstanding = [get_donation_outstanding(donation_entry, row.currency) for row in currencies]
			handed = frappe.db.exists(
				"Collector Handover Detail",
				{"donation_entry": donation_entry, "docstatus": 1},
			)
			status = "Handed Over" if all(not flt(value) for value in outstanding) else (
				"Partly Handed Over" if handed else "With Collector"
			)
			frappe.db.set_value("Donation Entry", donation_entry, "treasury_status", status, update_modified=False)


def get_donation_outstanding(donation_entry, currency, exclude_handover=None):
	donated = frappe.db.sql(
		"""select coalesce(sum(donation_amount), 0) from `tabDonation Payment Detail`
		where parent=%s and parenttype='Donation Entry' and currency=%s""",
		(donation_entry, currency),
	)[0][0]
	conditions = " and handover.name != %(exclude)s" if exclude_handover else ""
	handed = frappe.db.sql(
		f"""select coalesce(sum(line.amount), 0)
		from `tabCollector Handover Detail` line
		inner join `tabCollector Handover` handover on handover.name=line.parent
		where handover.docstatus=1 and line.donation_entry=%(donation)s
		and line.currency=%(currency)s {conditions}""",
		{"donation": donation_entry, "currency": currency, "exclude": exclude_handover},
	)[0][0]
	return flt(donated) - flt(handed)


@frappe.whitelist()
def get_custody_account(collector, currency):
	return frappe.db.get_value(
		"Collector Custody Account",
		{"parent": collector, "parenttype": "Collector Profile", "currency": currency},
		"account",
	)
