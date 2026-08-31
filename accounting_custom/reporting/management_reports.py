import frappe
from frappe import _
from frappe.utils import flt


def daily_treasury(filters):
	columns = [
		{"fieldname":"posting_date","label":_("Date"),"fieldtype":"Date","width":100},
		{"fieldname":"voucher_type","label":_("Document Type"),"fieldtype":"Data","width":170},
		{"fieldname":"voucher_no","label":_("Document"),"fieldtype":"Dynamic Link","options":"voucher_type","width":180},
		{"fieldname":"account","label":_("Account"),"fieldtype":"Link","options":"Account","width":220},
		{"fieldname":"currency","label":_("Currency"),"fieldtype":"Link","options":"Currency","width":90},
		{"fieldname":"received","label":_("Received"),"fieldtype":"Currency","options":"currency","width":120},
		{"fieldname":"paid","label":_("Paid"),"fieldtype":"Currency","options":"currency","width":120},
	]
	data = frappe.db.sql(
		"""select gle.posting_date, gle.voucher_type, gle.voucher_no, gle.account,
		gle.account_currency as currency, sum(gle.debit_in_account_currency) received,
		sum(gle.credit_in_account_currency) paid
		from `tabGL Entry` gle
		inner join `tabAccount` account_master on account_master.name=gle.account
		where gle.company=%(company)s and gle.posting_date between %(from_date)s and %(to_date)s
		and gle.is_cancelled=0 and gle.voucher_type in
		('Donation Entry','Collector Handover','Payment Memo','Accounting Payment Entry')
		and (account_master.account_type in ('Cash','Bank') or gle.account in
			(select custody.account from `tabCollector Custody Account` custody))
		group by gle.posting_date, gle.voucher_type, gle.voucher_no, gle.account, gle.account_currency
		order by gle.posting_date, gle.voucher_no""", filters, as_dict=True,
	)
	return columns, data


def collector_collections(filters):
	columns = [
		{"fieldname":"collector","label":_("Collector"),"fieldtype":"Link","options":"Collector Profile","width":180},
		{"fieldname":"posting_date","label":_("Date"),"fieldtype":"Date","width":100},
		{"fieldname":"donation_entry","label":_("Donation Entry"),"fieldtype":"Link","options":"Donation Entry","width":180},
		{"fieldname":"donor","label":_("Donor"),"fieldtype":"Link","options":"Donor","width":180},
		{"fieldname":"project","label":_("Project"),"fieldtype":"Link","options":"Project","width":160},
		{"fieldname":"currency","label":_("Currency"),"fieldtype":"Link","options":"Currency","width":90},
		{"fieldname":"amount","label":_("Amount"),"fieldtype":"Currency","options":"currency","width":120},
		{"fieldname":"treasury_status","label":_("Treasury Status"),"fieldtype":"Data","width":150},
	]
	conditions = " and donation.collector=%(collector)s" if filters.get("collector") else ""
	data = frappe.db.sql(
		f"""select donation.collector, donation.posting_date, donation.name donation_entry,
		donation.donor, donation.project, payment.currency, payment.donation_amount amount,
		donation.treasury_status
		from `tabDonation Entry` donation
		inner join `tabDonation Payment Detail` payment on payment.parent=donation.name
		where donation.docstatus=1 and donation.company=%(company)s
		and donation.posting_date between %(from_date)s and %(to_date)s {conditions}
		order by donation.posting_date, donation.collector""", filters, as_dict=True,
	)
	return columns, data


def donor_history(filters):
	columns = [
		{"fieldname":"posting_date","label":_("Date"),"fieldtype":"Date","width":100},
		{"fieldname":"donation_entry","label":_("Donation Entry"),"fieldtype":"Link","options":"Donation Entry","width":180},
		{"fieldname":"donor","label":_("Donor"),"fieldtype":"Link","options":"Donor","width":180},
		{"fieldname":"donor_name","label":_("Donor Name"),"fieldtype":"Data","width":180},
		{"fieldname":"project","label":_("Project"),"fieldtype":"Link","options":"Project","width":160},
		{"fieldname":"currency","label":_("Currency"),"fieldtype":"Link","options":"Currency","width":90},
		{"fieldname":"amount","label":_("Amount"),"fieldtype":"Currency","options":"currency","width":120},
	]
	conditions = " and donation.donor=%(donor)s" if filters.get("donor") else ""
	data = frappe.db.sql(
		f"""select donation.posting_date, donation.name donation_entry, donation.donor,
		donation.donor_name, donation.project, payment.currency, payment.donation_amount amount
		from `tabDonation Entry` donation
		inner join `tabDonation Payment Detail` payment on payment.parent=donation.name
		where donation.docstatus=1 and donation.company=%(company)s
		and donation.posting_date between %(from_date)s and %(to_date)s {conditions}
		order by donation.posting_date desc""", filters, as_dict=True,
	)
	return columns, data


def project_donations(filters):
	columns = [
		{"fieldname":"project","label":_("Project"),"fieldtype":"Link","options":"Project","width":220},
		{"fieldname":"currency","label":_("Currency"),"fieldtype":"Link","options":"Currency","width":100},
		{"fieldname":"amount","label":_("Total Donations"),"fieldtype":"Currency","options":"currency","width":160},
		{"fieldname":"donation_count","label":_("Receipts"),"fieldtype":"Int","width":90},
	]
	data = frappe.db.sql(
		"""select coalesce(donation.project, 'Unassigned') project, payment.currency,
		sum(payment.donation_amount) amount, count(distinct donation.name) donation_count
		from `tabDonation Entry` donation
		inner join `tabDonation Payment Detail` payment on payment.parent=donation.name
		where donation.docstatus=1 and donation.company=%(company)s
		and donation.posting_date between %(from_date)s and %(to_date)s
		group by donation.project, payment.currency order by donation.project""", filters, as_dict=True,
	)
	return columns, data


def pending_approvals(filters):
	columns = [
		{"fieldname":"document_type","label":_("Document Type"),"fieldtype":"Data","width":170},
		{"fieldname":"document","label":_("Document"),"fieldtype":"Dynamic Link","options":"document_type","width":190},
		{"fieldname":"posting_date","label":_("Date"),"fieldtype":"Date","width":100},
		{"fieldname":"status","label":_("Approval Status"),"fieldtype":"Data","width":190},
		{"fieldname":"owner","label":_("Owner"),"fieldtype":"Link","options":"User","width":180},
		{"fieldname":"amount","label":_("Amount"),"fieldtype":"Currency","width":120},
	]
	data = frappe.db.sql(
		"""select 'Donation Entry' document_type, name document, posting_date,
		approval_status status, owner, base_donation_amount amount
		from `tabDonation Entry` where docstatus=0 and company=%(company)s
		and approval_status in ('Pending Finance Approval','Returned')
		union all
		select 'Payment Memo', name, posting_date, approval_status, owner, total_amount
		from `tabPayment Memo` where docstatus=0 and company=%(company)s
		and approval_status not in ('Draft','Rejected')
		union all
		select 'Accounting Payment Entry', name, posting_date, approval_status, owner, total_debit
		from `tabAccounting Payment Entry` where docstatus=0 and company=%(company)s
		and approval_status in ('Pending Finance Approval','Returned')
		union all
		select 'Payroll Review', name, period_end, review_status, owner, 0
		from `tabPayroll Review` where company=%(company)s and review_status != 'Approved'
		union all
		select 'Employee Monthly Adjustment', name, payroll_date, 'Pending Finance', owner, total_deductions
		from `tabEmployee Monthly Adjustment` where company=%(company)s and docstatus=0
		order by posting_date""", filters, as_dict=True,
	)
	return columns, data


def open_custodies(filters):
	columns = [
		{"fieldname":"memo","label":_("Custody Memo"),"fieldtype":"Link","options":"Payment Memo","width":180},
		{"fieldname":"posting_date","label":_("Date"),"fieldtype":"Date","width":100},
		{"fieldname":"applicant_name","label":_("Applicant"),"fieldtype":"Data","width":180},
		{"fieldname":"currency","label":_("Currency"),"fieldtype":"Link","options":"Currency","width":90},
		{"fieldname":"custody_amount","label":_("Custody Amount"),"fieldtype":"Currency","options":"currency","width":140},
		{"fieldname":"closed_amount","label":_("Closed Amount"),"fieldtype":"Currency","options":"currency","width":140},
		{"fieldname":"outstanding","label":_("Outstanding"),"fieldtype":"Currency","options":"currency","width":140},
	]
	data = frappe.db.sql(
		"""select custody.name memo, custody.posting_date, custody.applicant_name, custody.currency,
		custody.total_amount custody_amount, coalesce(sum(closure.total_amount),0) closed_amount,
		custody.total_amount-coalesce(sum(closure.total_amount),0) outstanding
		from `tabPayment Memo` custody
		left join `tabPayment Memo` closure on closure.settlement_against=custody.name
		and closure.docstatus=1 and closure.payment_type='Custody Closure'
		where custody.docstatus=1 and custody.payment_type='Custody' and custody.company=%(company)s
		group by custody.name having outstanding > 0 order by custody.posting_date""", filters, as_dict=True,
	)
	return columns, data


def period_balance_comparison(filters, cash_bank=False):
	columns = [
		{"fieldname":"dimension","label":_("Account" if cash_bank else "Cost Center"),"fieldtype":"Data","width":240},
		{"fieldname":"previous_balance","label":_("Previous Period"),"fieldtype":"Currency","width":150},
		{"fieldname":"current_balance","label":_("Current Period"),"fieldtype":"Currency","width":150},
		{"fieldname":"change","label":_("Change"),"fieldtype":"Currency","width":140},
	]
	dimension = "gle.account" if cash_bank else "coalesce(gle.cost_center, 'Unassigned')"
	account_join = "inner join `tabAccount` account on account.name=gle.account" if cash_bank else ""
	account_condition = "and account.account_type in ('Cash','Bank')" if cash_bank else ""
	data = frappe.db.sql(
		f"""select {dimension} dimension,
		sum(case when gle.posting_date <= %(previous_to)s then gle.debit-gle.credit else 0 end) previous_balance,
		sum(case when gle.posting_date <= %(current_to)s then gle.debit-gle.credit else 0 end) current_balance,
		sum(case when gle.posting_date <= %(current_to)s then gle.debit-gle.credit else 0 end)
		-sum(case when gle.posting_date <= %(previous_to)s then gle.debit-gle.credit else 0 end) change
		from `tabGL Entry` gle {account_join}
		where gle.company=%(company)s and gle.is_cancelled=0 {account_condition}
		group by {dimension} order by {dimension}""", filters, as_dict=True,
	)
	return columns, data


def monthly_cost_center_movement(filters):
	columns = [
		{"fieldname":"cost_center","label":_("Cost Center"),"fieldtype":"Link","options":"Cost Center","width":220},
		{"fieldname":"opening","label":_("Opening / YTD"),"fieldtype":"Currency","width":140},
		{"fieldname":"revenue","label":_("Revenue"),"fieldtype":"Currency","width":140},
		{"fieldname":"expense","label":_("Expense"),"fieldtype":"Currency","width":140},
		{"fieldname":"ending","label":_("Ending Balance"),"fieldtype":"Currency","width":150},
	]
	data = frappe.db.sql(
		"""select gle.cost_center,
		sum(case when gle.posting_date < %(year_start)s then gle.debit-gle.credit else 0 end) opening,
		sum(case when account.root_type='Income' and gle.posting_date between %(from_date)s and %(to_date)s then gle.credit-gle.debit else 0 end) revenue,
		sum(case when account.root_type='Expense' and gle.posting_date between %(from_date)s and %(to_date)s then gle.debit-gle.credit else 0 end) expense,
		sum(case when gle.posting_date <= %(to_date)s then gle.debit-gle.credit else 0 end) ending
		from `tabGL Entry` gle inner join `tabAccount` account on account.name=gle.account
		where gle.company=%(company)s and gle.is_cancelled=0 and gle.cost_center is not null
		group by gle.cost_center order by gle.cost_center""", filters, as_dict=True,
	)
	return columns, data


def balance_sheet_by_cost_center(filters):
	columns = [
		{"fieldname":"cost_center","label":_("Cost Center"),"fieldtype":"Link","options":"Cost Center","width":220},
		{"fieldname":"root_type","label":_("Section"),"fieldtype":"Data","width":120},
		{"fieldname":"account","label":_("Account"),"fieldtype":"Link","options":"Account","width":240},
		{"fieldname":"balance","label":_("Balance"),"fieldtype":"Currency","width":150},
	]
	data = frappe.db.sql(
		"""select gle.cost_center, account.root_type, gle.account,
		sum(gle.debit-gle.credit) balance
		from `tabGL Entry` gle inner join `tabAccount` account on account.name=gle.account
		where gle.company=%(company)s and gle.is_cancelled=0 and gle.posting_date <= %(to_date)s
		and gle.cost_center is not null and account.root_type in ('Asset','Liability','Equity')
		group by gle.cost_center, account.root_type, gle.account
		having abs(balance) > 0.000001
		order by gle.cost_center, field(account.root_type,'Asset','Liability','Equity'), gle.account""",
		filters, as_dict=True,
	)
	return columns, data
