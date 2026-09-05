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
	if "للدعوة والتعليم الشرعي والمؤسسات الخيرية" in html:
		return html
	return html.replace(
		"جمعية الاتحاد الإسلامي",
		"""جمعية الاتحاد الإسلامي
            <span style="font-size:14px;font-weight:700;">للدعوة والتعليم الشرعي والمؤسسات الخيرية</span>
            <span style="font-size:13px;font-weight:700;">لبنان - علم وخبر ١٤٥/أد</span>""",
		1,
	)


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
