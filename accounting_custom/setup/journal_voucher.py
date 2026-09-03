import frappe


PRINT_FORMAT_NAME = "Journal Voucher"

JOURNAL_VOUCHER_HTML = r"""
{% set company_arabic = frappe.db.get_value("Company", doc.company, "custom_company_name_arabic") or doc.company %}
{% set posting_year = (doc.posting_date|string).split("-")[0] if doc.posting_date else "" %}
{% set totals = namespace(lbp_debit=0, lbp_credit=0, usd_debit=0, usd_credit=0) %}

<style>
@page { size: A4 landscape; margin: 9mm; }
.journal-voucher { color:#111; font-family:"Times New Roman",Tahoma,serif; font-size:11px; }
.journal-voucher * { box-sizing:border-box; }
.jv-company { margin-bottom:8px; font-size:18px; font-weight:700; }
.jv-title { margin:0 0 24px; text-align:center; font-size:21px; font-weight:700; }
.jv-meta { display:flex; flex-wrap:wrap; gap:34px; margin:0 5px 7px; font-size:14px; font-weight:700; }
.jv-meta span { white-space:nowrap; }
.jv-table { width:100%; table-layout:fixed; border-collapse:collapse; }
.jv-table th,.jv-table td { border:1px solid #aaa; padding:5px 4px; vertical-align:top; }
.jv-table th { text-align:center; font-weight:700; }
.jv-table .account { direction:ltr; text-align:left; }
.jv-table .narration { line-height:1.25; }
.jv-table .arabic { direction:rtl; text-align:left; font-family:Tahoma,Arial,sans-serif; }
.jv-table .number { direction:ltr; text-align:right; white-space:nowrap; }
.jv-table .center { text-align:center; }
.jv-table tbody td { min-height:42px; }
.jv-total-label { text-align:center; font-size:15px; font-weight:700; }
.jv-signatures { display:flex; gap:90px; margin:18px 15px 0; font-size:14px; font-weight:700; }
.jv-signature { min-width:160px; padding-top:4px; border-bottom:1px solid #aaa; }
.print-heading { display:none !important; }
</style>

<div class="journal-voucher">
  <div class="jv-company" dir="rtl">{{ company_arabic }} {{ posting_year }}</div>
  <div class="jv-title">Journal Voucher</div>
  <div class="jv-meta">
    <span>Journal Voucher No : {{ doc.name }}</span>
    <span>Entered in : {{ frappe.utils.formatdate(doc.posting_date, "dd/MM/yyyy") }}</span>
    <span>JV Ref : {{ doc.cheque_no or "" }}</span>
  </div>

  <table class="jv-table">
    <colgroup>
      <col style="width:7%"><col style="width:22%"><col style="width:7%"><col style="width:8%">
      <col style="width:7%"><col style="width:7%"><col style="width:5%"><col style="width:9%">
      <col style="width:7%"><col style="width:7%"><col style="width:7%"><col style="width:7%">
    </colgroup>
    <thead>
      <tr>
        <th>Account</th><th>Name / Narration</th><th>V. Date</th><th>Job</th>
        <th>Ref.</th><th>User Ref.</th><th>Type</th><th>Foreign Currency</th>
        <th>LBP Debit</th><th>LBP Credit</th><th>USD Debit</th><th>USD Credit</th>
      </tr>
    </thead>
    <tbody>
    {% for row in doc.accounts %}
      {% set account_number = frappe.db.get_value("Account", row.account, "account_number") or row.account %}
      {% set account_name = frappe.db.get_value("Account", row.account, "account_name") or row.account %}
      {% set account_arabic = frappe.db.get_value("Account", row.account, "custom_account_name_arabic") or "" %}
      {% set lbp_debit = row.debit_in_account_currency if row.account_currency == "LBP" else 0 %}
      {% set lbp_credit = row.credit_in_account_currency if row.account_currency == "LBP" else 0 %}
      {% set usd_debit = row.debit_in_account_currency if row.account_currency == "USD" else 0 %}
      {% set usd_credit = row.credit_in_account_currency if row.account_currency == "USD" else 0 %}
      {% set totals.lbp_debit = totals.lbp_debit + (lbp_debit or 0) %}
      {% set totals.lbp_credit = totals.lbp_credit + (lbp_credit or 0) %}
      {% set totals.usd_debit = totals.usd_debit + (usd_debit or 0) %}
      {% set totals.usd_credit = totals.usd_credit + (usd_credit or 0) %}
      <tr>
        <td class="account">{{ account_number }}</td>
        <td class="narration">
          {% if account_arabic %}<div class="arabic">{{ account_arabic }}</div>{% endif %}
          <div>{{ account_name }}</div>
          {% if row.user_remark %}<div>{{ row.user_remark }}</div>{% endif %}
        </td>
        <td class="center">{{ frappe.utils.formatdate(doc.posting_date, "dd/MM/yyyy") }}</td>
        <td>{{ row.project or row.cost_center or "" }}</td>
        <td>{{ row.reference_name or "" }}</td>
        <td>{{ row.user_remark or "" }}</td>
        <td class="center">GJV</td>
        <td class="number">{% if row.account_currency not in ("LBP", "USD") %}{{ row.debit_in_account_currency or row.credit_in_account_currency or 0 }} {{ row.account_currency }}{% endif %}</td>
        <td class="number">{% if lbp_debit %}{{ frappe.utils.fmt_money(lbp_debit, currency="") }}{% endif %}</td>
        <td class="number">{% if lbp_credit %}{{ frappe.utils.fmt_money(lbp_credit, currency="") }}{% endif %}</td>
        <td class="number">{% if usd_debit %}{{ frappe.utils.fmt_money(usd_debit, currency="") }}{% endif %}</td>
        <td class="number">{% if usd_credit %}{{ frappe.utils.fmt_money(usd_credit, currency="") }}{% endif %}</td>
      </tr>
    {% endfor %}
      <tr>
        <td colspan="8" class="jv-total-label">Total :</td>
        <td class="number">{{ frappe.utils.fmt_money(totals.lbp_debit, currency="") }}</td>
        <td class="number">{{ frappe.utils.fmt_money(totals.lbp_credit, currency="") }}</td>
        <td class="number">{{ frappe.utils.fmt_money(totals.usd_debit, currency="") }}</td>
        <td class="number">{{ frappe.utils.fmt_money(totals.usd_credit, currency="") }}</td>
      </tr>
    </tbody>
  </table>

  <div class="jv-signatures">
    <div class="jv-signature">Accountant</div>
    <div class="jv-signature">Approved by</div>
  </div>
</div>
"""


def ensure_journal_voucher_print_format():
	if not frappe.db.exists("DocType", "Journal Entry"):
		return
	values = {
		"doc_type": "Journal Entry",
		"module": "Accounting Custom",
		"standard": "No",
		"custom_format": 1,
		"disabled": 0,
		"print_format_type": "Jinja",
		"raw_printing": 0,
		"html": JOURNAL_VOUCHER_HTML,
		"margin_top": 0,
		"margin_bottom": 0,
		"margin_left": 0,
		"margin_right": 0,
		"font_size": 11,
	}
	if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
		frappe.db.set_value("Print Format", PRINT_FORMAT_NAME, values, update_modified=False)
	else:
		frappe.get_doc({
			"doctype": "Print Format",
			"name": PRINT_FORMAT_NAME,
			**values,
		}).insert(ignore_permissions=True)
