import frappe


def execute():
	for row in frappe.db.sql(
		"""
		select
			parent,
			sum(case when currency = 'USD' then donation_amount else 0 end) as total_usd,
			sum(case when currency = 'LBP' then donation_amount else 0 end) as total_lbp
		from `tabDonation Payment Detail`
		where parenttype = 'Donation Entry'
		group by parent
		""",
		as_dict=True,
	):
		frappe.db.set_value(
			"Donation Entry",
			row.parent,
			{"total_usd": row.total_usd or 0, "total_lbp": row.total_lbp or 0},
			update_modified=False,
		)
