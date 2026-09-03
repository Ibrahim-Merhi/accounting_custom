import frappe
from frappe.desk.reportview import get_match_cond


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def mode_of_payment_by_company(doctype, txt, searchfield, start, page_len, filters):
	company = (filters or {}).get("company")
	if not company:
		return []
	return frappe.db.sql(
		"""
		select distinct mode.name, mode.type
		from `tabMode of Payment` mode
		inner join `tabMode of Payment Account` account
			on account.parent = mode.name
			and account.parenttype = 'Mode of Payment'
		where mode.enabled = 1
			and account.company = %(company)s
			and ifnull(account.default_account, '') != ''
			and (mode.name like %(txt)s or ifnull(mode.type, '') like %(txt)s)
			{match_condition}
		order by mode.name
		limit %(page_len)s offset %(start)s
		""".format(match_condition=get_match_cond("Mode of Payment")),
		{"company": company, "txt": f"%{txt}%", "page_len": page_len, "start": start},
	)
