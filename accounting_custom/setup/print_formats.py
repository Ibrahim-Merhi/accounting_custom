import re

import frappe


RECEIPT_NAME = "سند قبض"
PAYMENT_NAME = "سند صرف"
ACCOUNTING_RECEIPT_NAME = "سند قبض محاسبي"
MUNTADA_CONDITIONAL_START = "{# MUNTADA-COMPANY-CONDITIONAL-START #}"
MUNTADA_CONDITIONAL_END = "{# MUNTADA-COMPANY-CONDITIONAL-END #}"


def ensure_arabic_voucher_print_formats():
	if not frappe.db.exists("DocType", "Donation Entry"):
		return

	receipt = frappe.get_doc("Print Format", RECEIPT_NAME)
	standard_receipt_html = _add_organization_details(
		_add_voucher_number(_standard_company_html(receipt.html))
	)
	receipt_html = _company_conditional_html(
		standard_receipt_html,
		_muntada_voucher_html(payment=False, donation=True),
		_islam_forum_html(standard_receipt_html),
	)
	if receipt_html != receipt.html:
		receipt.db_set("html", receipt_html, update_modified=False)

	if not frappe.db.exists("DocType", "Accounting Payment Entry"):
		return

	payment_html = _company_conditional_html(
		_payment_html(standard_receipt_html),
		_muntada_voucher_html(payment=True),
		_islam_forum_html(_payment_html(standard_receipt_html)),
	)
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
			"html": _company_conditional_html(
				_accounting_receipt_html(standard_receipt_html),
				_muntada_voucher_html(payment=False),
				_islam_forum_html(_accounting_receipt_html(standard_receipt_html)),
			),
		}
		if frappe.db.exists("Print Format", ACCOUNTING_RECEIPT_NAME):
			frappe.db.set_value(
				"Print Format", ACCOUNTING_RECEIPT_NAME, receipt_values, update_modified=False
			)
		else:
			frappe.get_doc({
				"doctype": "Print Format", "name": ACCOUNTING_RECEIPT_NAME, **receipt_values,
			}).insert(ignore_permissions=True)

	# Earlier app versions created separate company-specific formats. The
	# conditional design now lives inside the existing format for each DocType.
	for obsolete_name in ("سند صرف - المنتدى الطلابي", "سند قبض - المنتدى الطلابي"):
		if frappe.db.exists("Print Format", obsolete_name):
			frappe.delete_doc("Print Format", obsolete_name, ignore_permissions=True)


def _standard_company_html(html):
	"""Return the standard branch of an already-wrapped format."""
	if MUNTADA_CONDITIONAL_START not in html:
		return html
	standard_start = html.find("{% else %}") + len("{% else %}")
	standard_end = html.rfind("{% endif %}\n" + MUNTADA_CONDITIONAL_END)
	if standard_start < len("{% else %}") or standard_end < standard_start:
		return html
	return html[standard_start:standard_end].strip()


def _company_conditional_html(standard_html, muntada_html, islam_forum_html=None):
	islam_forum_html = islam_forum_html or standard_html
	return f"""{MUNTADA_CONDITIONAL_START}
{{% if doc.company == "Al Muntada Al Tullabi" %}}
{muntada_html}
{{% elif doc.company == "Al Muntada Islam Forum" %}}
{islam_forum_html}
{{% else %}}
{standard_html}
{{% endif %}}
{MUNTADA_CONDITIONAL_END}"""


def _islam_forum_html(html):
	organization = """<div class="organization-name organization-layout-v2">
            <span class="organization-primary">جمعية الثقافة والتوجيه الاجتماعي</span>
            <span class="organization-registration">علم وخبر ٣٢٥ أ٫د</span>
        </div>"""
	html = re.sub(
		r'<div class="organization-name(?: organization-layout-v2)?">.*?</div>',
		organization,
		html,
		count=1,
		flags=re.DOTALL,
	)
	logo = "/assets/accounting_custom/images/print_formats/al_muntada_islam_forum_grayscale.png"
	html = re.sub(r'(<img\s+[^>]*?src=")[^"]+("[^>]*>)', rf'\g<1>{logo}\g<2>', html, count=1)
	return html


def _muntada_voucher_html(payment, donation=False):
	title = "سند صرف" if payment else "سند قبض"
	party_label = "يُصرف إلى:" if payment else "وصلنا من:"
	verse = (
		"﴿وَمَا تُنفِقُوا مِنْ شَيْءٍ فَإِنَّ اللَّهَ بِهِ عَلِيمٌ﴾"
		if payment else
		"﴿وَمَا أَنفَقْتُم مِّن شَيْءٍ فَهُوَ يُخْلِفُهُ وَهُوَ خَيْرُ الرَّازِقِينَ﴾"
	)
	signatures = (
		'<td>المسؤول:<div class="sign-line"></div></td>'
		'<td>أمين الصندوق:<div class="sign-line"></div></td>'
		'<td>المستلم:<div class="sign-line"></div></td>'
		if payment else
		'<td>التاريخ: <span dir="ltr">{{ doc.posting_date or "" }}</span></td>'
		'<td>أمين الصندوق:<div class="sign-line"></div></td>'
		'<td>المستلم:<div class="sign-line"></div></td>'
	)
	rows_field = "payments" if donation else "custom_accounting_rows_copy"
	amount_field = "donation_amount" if donation else "total_debit"
	return f"""
{{% set voucher_rows = doc.{rows_field} or [] %}}
{{% set usd_amount = voucher_rows | selectattr("currency", "equalto", "USD") | sum(attribute="{amount_field}") %}}
{{% set lbp_amount = voucher_rows | selectattr("currency", "equalto", "LBP") | sum(attribute="{amount_field}") %}}
{{% set parties = (doc.donor_name or doc.donor or "") if {str(donation).lower()} else (voucher_rows | map(attribute="party_name") | select | unique | join("، ")) %}}
{{% set payment_modes = voucher_rows | map(attribute="mode_of_payment") | select | join(" ") %}}
{{% set company_logo = frappe.db.get_value("Company", doc.company, "company_logo") or "" %}}
<style>
@page {{ size: A5 landscape; margin: 5mm; }}
.print-format {{ margin:0!important; padding:0!important; }}
.muntada-voucher {{ direction:rtl; font-family:"Traditional Arabic","Arial",sans-serif; color:#211f20;
    width:100%; min-height:132mm; position:relative; box-sizing:border-box; padding:8mm 31mm 5mm 10mm; }}
.muntada-sidebar {{ position:absolute; top:0; right:0; bottom:0; width:27mm; background:#000; color:#fff;
    display:flex; align-items:center; justify-content:center; writing-mode:vertical-rl; transform:rotate(180deg);
    font-size:22px; font-weight:800; text-align:center; }}
.muntada-head {{ display:grid; grid-template-columns:30mm 1fr; gap:7mm; direction:ltr; align-items:center; }}
.muntada-logo {{ width:28mm; height:28mm; object-fit:contain; filter:grayscale(1); }}
.muntada-logo-space {{ width:28mm; height:28mm; border:2px solid #222; }}
.muntada-heading {{ direction:rtl; text-align:center; }}
.muntada-basmala {{ font-size:13px; margin-bottom:2px; }}
.muntada-verse {{ font-size:25px; font-weight:700; white-space:nowrap; }}
.muntada-title {{ background:#000; color:#fff; font-size:28px; line-height:1.15; text-align:center;
    font-weight:700; margin:4mm 0 4mm; padding:2mm; }}
.muntada-amounts {{ direction:ltr; margin-top:2mm; }}
.amount-box {{ display:inline-block; border:2px solid #222; min-width:31mm; padding:2mm 3mm;
    font-family:Arial,sans-serif; font-size:15px; font-weight:700; text-align:center; }}
.voucher-row {{ font-size:21px; font-weight:700; margin:3mm 0; white-space:nowrap; }}
.dots {{ display:inline-block; border-bottom:2px dotted #333; min-width:62%; min-height:7mm;
    padding:0 2mm; font-size:18px; font-weight:500; vertical-align:bottom; }}
.short-dots {{ min-width:24%; }}
.check {{ display:inline-block; width:6mm; height:6mm; border:2px solid #222; margin:0 2mm;
    text-align:center; line-height:5mm; font-family:Arial; }}
.muntada-signatures {{ width:100%; border-top:3px solid #222; margin-top:5mm; padding-top:2mm;
    table-layout:fixed; font-size:17px; font-weight:700; text-align:center; }}
.sign-line {{ border-bottom:2px dotted #333; height:8mm; margin:0 4mm; }}
.muntada-footer {{ border:2px solid #222; margin-top:3mm; padding:1.5mm; text-align:center;
    font-size:12px; font-weight:700; white-space:nowrap; }}
</style>
<div class="muntada-voucher">
  <div class="muntada-sidebar">جمعية المنتدى الطلابي&nbsp;&nbsp; لبنان - علم وخبر</div>
  <div class="muntada-head">
    {{% if company_logo %}}<img class="muntada-logo" src="{{{{ company_logo }}}}">{{% else %}}<div class="muntada-logo-space"></div>{{% endif %}}
    <div class="muntada-heading"><div class="muntada-basmala">بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</div><div class="muntada-verse">{verse}</div></div>
  </div>
  <div class="muntada-amounts"><span class="amount-box">$ {{{{ "{{:,.2f}}".format(usd_amount or 0) }}}}</span><span class="amount-box">{{{{ "{{:,.0f}}".format(lbp_amount or 0) }}}} ل.ل</span></div>
  <div class="muntada-title">{title}</div>
  <div class="voucher-row">{party_label} <span class="dots">{{{{ parties }}}}</span> رقم الجوال: <span class="dots short-dots"></span></div>
  <div class="voucher-row">مبلغ وقدره: <span class="dots">{{{{ doc.custom_amount_in_words_arabic or "" }}}}</span> فقط لا غير</div>
  <div class="voucher-row">نقدي <span class="check">{{% if "cash" in payment_modes|lower %}}✓{{% endif %}}</span> شيك رقم: <span class="dots short-dots"></span> مسحوب على بنك: <span class="dots short-dots"></span></div>
  <div class="voucher-row">وذلك لحساب: <span class="dots">{{{{ doc.remarks or "" }}}}</span></div>
  <table class="muntada-signatures"><tr>{signatures}</tr></table>
  <div class="muntada-footer">هاتف: بيروت: 01/644660 - 01/651990 &nbsp;–&nbsp; طرابلس: 06/442638 &nbsp;–&nbsp; البقاع: 03/819357 &nbsp;–&nbsp; صيدا: 07/735074</div>
</div>
"""


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
    margin-right: 126px !important;
}
.organization-box {
    width: 112px !important;
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
    gap: 2px;
    padding: 7px 3px;
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
    font-size: 27px;
    font-weight: 800;
    line-height: 1.05;
}
.organization-layout-v2 .organization-secondary {
    flex: 0 0 29%;
    font-size: 14px;
    font-weight: 700;
    line-height: 1.15;
}
.organization-layout-v2 .organization-registration {
    flex: 0 0 15%;
    font-size: 10px;
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
	html = html.replace('{{ user.full_name or "" }}', "", 1)
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
