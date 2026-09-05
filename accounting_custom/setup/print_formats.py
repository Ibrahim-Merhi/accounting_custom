import re

import frappe


RECEIPT_NAME = "سند قبض"
PAYMENT_NAME = "سند صرف"
ACCOUNTING_RECEIPT_NAME = "سند قبض محاسبي"


def ensure_arabic_voucher_print_formats():
	if not frappe.db.exists("DocType", "Donation Entry"):
		return

	receipt = frappe.get_doc("Print Format", RECEIPT_NAME)
	receipt_html = _add_organization_details(_add_voucher_number(receipt.html))
	if receipt_html != receipt.html:
		receipt.db_set("html", receipt_html, update_modified=False)

	if not frappe.db.exists("DocType", "Accounting Payment Entry"):
		return

	payment_html = _payment_html(receipt_html)
	values = {
		"doc_type": "Accounting Payment Entry",
		"module": "Accounting Custom",
		"default_print_language": "ar",
		"standard": "No",
		"custom_format": 1,
		"disabled": 0,
		"print_format_type": "Jinja",
		"raw_printing": 0,
		"html": payment_html,
		"margin_top": receipt.margin_top,
		"margin_bottom": receipt.margin_bottom,
		"margin_left": receipt.margin_left,
		"margin_right": receipt.margin_right,
		"font_size": receipt.font_size,
		"page_number": receipt.page_number,
	}
	if frappe.db.exists("Print Format", PAYMENT_NAME):
		frappe.db.set_value("Print Format", PAYMENT_NAME, values, update_modified=False)
	else:
		frappe.get_doc({"doctype": "Print Format", "name": PAYMENT_NAME, **values}).insert(
			ignore_permissions=True
		)

	if frappe.db.exists("DocType", "Accounting Receipt Entry"):
		receipt_values = {
			**values,
			"doc_type": "Accounting Receipt Entry",
			"html": _accounting_receipt_html(receipt_html),
		}
		if frappe.db.exists("Print Format", ACCOUNTING_RECEIPT_NAME):
			frappe.db.set_value(
				"Print Format", ACCOUNTING_RECEIPT_NAME, receipt_values, update_modified=False
			)
		else:
			frappe.get_doc({
				"doctype": "Print Format", "name": ACCOUNTING_RECEIPT_NAME, **receipt_values,
			}).insert(ignore_permissions=True)


def _add_organization_details(html):
	panel = """<div class="organization-name organization-layout-v2">
            <span class="organization-primary">جمعية الاتحاد الإسلامي</span>
            <span class="organization-secondary">للدعوة والتعليم الشرعي والمؤسسات الخيرية</span>
            <span class="organization-registration">لبنان - علم وخبر ١٤٥/أد</span>
        </div>"""
	html = re.sub(
		r'<div class="organization-name(?: organization-layout-v2)?">.*?</div>',
		panel,
		html,
		count=1,
		flags=re.DOTALL,
	)
	if "ITIHAD-ORGANIZATION-LAYOUT-V2" in html:
		return html
	styles = """
/* ITIHAD-ORGANIZATION-LAYOUT-V2 */
.receipt-main {
    margin-right: 164px !important;
}
.organization-box {
    width: 150px !important;
    background: #fff !important;
    color: #111 !important;
    border: 2px solid #111 !important;
}
.organization-name.organization-layout-v2 {
    writing-mode: horizontal-tb !important;
    transform: none !important;
    display: flex !important;
    flex-direction: row !important;
    direction: ltr !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 3px;
    padding: 8px 5px;
    box-sizing: border-box;
    background: #fff !important;
    color: #111 !important;
}
.organization-layout-v2 > span {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #111 !important;
    text-align: center;
    white-space: nowrap;
}
.organization-layout-v2 .organization-primary {
    flex: 0 0 52%;
    font-size: 32px;
    font-weight: 800;
    line-height: 1.05;
}
.organization-layout-v2 .organization-secondary {
    flex: 0 0 29%;
    font-size: 17px;
    font-weight: 700;
    line-height: 1.15;
}
.organization-layout-v2 .organization-registration {
    flex: 0 0 15%;
    font-size: 12px;
    font-weight: 700;
    line-height: 1.1;
}
"""
	return html.replace("</style>", f"{styles}\n</style>", 1)


def _add_voucher_number(html):
	if "voucher-number" in html:
		return html
	marker = """                    </div>\n\n\n\n                    <!-- =====================================\n                         CURRENCY BOXES"""
	number = """                    </div>\n\n                    <div class=\"voucher-number\" dir=\"rtl\" style=\"margin:4px auto 0; font-size:14px; font-weight:700;\">\n                        رقم السند: <span dir=\"ltr\" style=\"font-family:Arial,sans-serif !important;\">{{ doc.name }}</span>\n                    </div>\n\n\n\n                    <!-- =====================================\n                         CURRENCY BOXES"""
	return html.replace(marker, number, 1)


def _payment_html(html):
	old_amounts = """{% if doc.payments %}
    {% set usd_amount = doc.payments
        | selectattr(\"currency\", \"equalto\", \"USD\")
        | sum(attribute=\"donation_amount\") %}
    {% set lbp_amount = doc.payments
        | selectattr(\"currency\", \"equalto\", \"LBP\")
        | sum(attribute=\"donation_amount\") %}
{% else %}
    {% set usd_amount = doc.donation_amount if doc.currency == \"USD\" else 0 %}
    {% set lbp_amount = doc.donation_amount if doc.currency == \"LBP\" else 0 %}
{% endif %}"""
	new_amounts = """{% set usd_amount = doc.currency_totals
    | selectattr(\"currency\", \"equalto\", \"USD\")
    | sum(attribute=\"total_debit\") %}
{% set lbp_amount = doc.currency_totals
    | selectattr(\"currency\", \"equalto\", \"LBP\")
    | sum(attribute=\"total_debit\") %}"""

	html = html.replace("ITIHAD - DONATION ENTRY RECEIPT", "ITIHAD - PAYMENT ENTRY DISBURSEMENT")
	html = html.replace('"Donation Entry",\n    doc.name,', '"Accounting Payment Entry",\n    doc.name,', 1)
	html = html.replace(old_amounts, new_amounts, 1)
	html = html.replace("سند قبض", "سند صرف")
	html = html.replace("وصلنا من:", "يُصرف إلى:", 1)
	html = html.replace('{{ doc.donor_name or doc.donor or "" }}', '{{ doc.custom_accounting_rows_copy | map(attribute="party_name") | select | unique | join("، ") }}', 1)
	html = html.replace("DONOR NAME + PHONE", "PAYEE + REFERENCE")
	html = html.replace("رقم الهاتف:", "الفرع:", 1)
	html = html.replace("{{ donor_phone }}", '{{ doc.custom_branch or "" }}', 1)
	html = html.replace("وذلك لحساب:", "وذلك عن:", 1)
	html = html.replace("المستلم", "المستفيد", 1)
	return html


def _accounting_receipt_html(html):
	old_amounts = """{% if doc.payments %}
    {% set usd_amount = doc.payments
        | selectattr("currency", "equalto", "USD")
        | sum(attribute="donation_amount") %}
    {% set lbp_amount = doc.payments
        | selectattr("currency", "equalto", "LBP")
        | sum(attribute="donation_amount") %}
{% else %}
    {% set usd_amount = doc.donation_amount if doc.currency == "USD" else 0 %}
    {% set lbp_amount = doc.donation_amount if doc.currency == "LBP" else 0 %}
{% endif %}"""
	new_amounts = """{% set usd_amount = doc.currency_totals
    | selectattr("currency", "equalto", "USD")
    | sum(attribute="total_debit") %}
{% set lbp_amount = doc.currency_totals
    | selectattr("currency", "equalto", "LBP")
    | sum(attribute="total_debit") %}"""

	html = html.replace("ITIHAD - DONATION ENTRY RECEIPT", "ITIHAD - ACCOUNTING RECEIPT ENTRY")
	html = html.replace('"Donation Entry",\n    doc.name,', '"Accounting Receipt Entry",\n    doc.name,', 1)
	html = html.replace(old_amounts, new_amounts, 1)
	html = html.replace(
		'{{ doc.donor_name or doc.donor or "" }}',
		'{{ doc.custom_accounting_rows_copy | map(attribute="party_name") | select | unique | join("، ") }}',
		1,
	)
	html = html.replace("DONOR NAME + PHONE", "RECEIPT PARTY + REFERENCE")
	html = html.replace("رقم الهاتف:", "الفرع:", 1)
	html = html.replace("{{ donor_phone }}", '{{ doc.custom_branch or "" }}', 1)
	html = html.replace("وذلك لحساب:", "وذلك عن:", 1)
	return html
