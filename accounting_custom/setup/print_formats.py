import re

import frappe


RECEIPT_NAME = "سند قبض"
PAYMENT_NAME = "سند صرف"
ACCOUNTING_RECEIPT_NAME = "سند قبض محاسبي"
MUNTADA_CONDITIONAL_START = "{# MUNTADA-COMPANY-CONDITIONAL-START #}"
MUNTADA_CONDITIONAL_END = "{# MUNTADA-COMPANY-CONDITIONAL-END #}"
DONOR_DISPLAY_START = "{# DONATION-DONOR-DISPLAY-START #}"
DONOR_DISPLAY_END = "{# DONATION-DONOR-DISPLAY-END #}"
TREASURER_SIGNATURE = "/assets/accounting_custom/images/print_formats/treasurer_signature.jpg"
LEGACY_TREASURER_SIGNATURES = (
	"https://i.imgur.com/t8U9lax.png",
	"https://imgur.com/t8U9lax.png",
)


def ensure_arabic_voucher_print_formats():
	if not frappe.db.exists("DocType", "Donation Entry"):
		return

	receipt = frappe.get_doc("Print Format", RECEIPT_NAME)
	standard_receipt_html = _add_treasurer_signature(_donation_donor_display_html(
		_add_organization_details(_add_voucher_number(_standard_company_html(receipt.html)))
	))
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


def _donation_donor_display_html(html):
	"""Show an anonymous label or the donor's professional title on donation receipts."""
	if DONOR_DISPLAY_START in html:
		return html
	donor_expression = '{{ doc.donor_name or doc.donor or "" }}'
	donor_display = f"""{DONOR_DISPLAY_START}
{{% if doc.is_anonymous_male %}}
فاعل خير
{{% elif doc.is_anonymous_female %}}
فاعلة خير
{{% else %}}
{{% set professional_title = frappe.db.get_value("Donor", doc.donor, "professional_title") if doc.donor else "" %}}
{{{{ ((professional_title ~ " ") if professional_title else "") ~ (doc.donor_name or doc.donor or "") }}}}
{{% endif %}}
{DONOR_DISPLAY_END}"""
	return html.replace(donor_expression, donor_display)


def _add_treasurer_signature(html):
	"""Use the bundled treasurer signature in every standard voucher format."""
	for image_url in LEGACY_TREASURER_SIGNATURES:
		html = html.replace(image_url, TREASURER_SIGNATURE)
	return html


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
		f'<td>أمين الصندوق:<div class="treasurer-signature"><img src="{TREASURER_SIGNATURE}" alt="توقيع أمين الصندوق"></div></td>'
		'<td>المستلم:<div class="sign-line"></div></td>'
		if payment else
		'<td></td>'
		f'<td>أمين الصندوق:<div class="treasurer-signature"><img src="{TREASURER_SIGNATURE}" alt="توقيع أمين الصندوق"></div></td>'
		'<td>المستلم:<div class="sign-line"></div></td>'
	)
	date_line = (
		'<div class="muntada-date">'
		'التاريخ الهجري: <span dir="ltr">{{ doc.custom_hijri_date or "" }}</span>'
		'<span class="date-separator">|</span>'
		'التاريخ الميلادي: <span dir="ltr">{{ doc.posting_date or "" }}</span>'
		'</div>'
	)
	amount_rows_field = "payments" if donation else "currency_totals"
	payment_rows_field = "payments" if donation else "custom_accounting_rows_copy"
	amount_field = "donation_amount" if donation else "total_debit"
	return f"""
{{% set amount_rows = doc.{amount_rows_field} or [] %}}
{{% set payment_rows = doc.{payment_rows_field} or [] %}}
{{% set usd_amount = amount_rows | selectattr("currency", "equalto", "USD") | sum(attribute="{amount_field}") %}}
{{% set lbp_amount = amount_rows | selectattr("currency", "equalto", "LBP") | sum(attribute="{amount_field}") %}}
{{% set donor_professional_title = frappe.db.get_value("Donor", doc.donor, "professional_title") if {str(donation).lower()} and doc.donor else "" %}}
{{% set donor_display_name = "فاعل خير" if doc.is_anonymous_male else ("فاعلة خير" if doc.is_anonymous_female else (((donor_professional_title ~ " ") if donor_professional_title else "") ~ (doc.donor_name or doc.donor or ""))) %}}
{{% set parties = donor_display_name if {str(donation).lower()} else (payment_rows | map(attribute="party_name") | select | unique | join("، ")) %}}
{{% set payment_modes = payment_rows | map(attribute="mode_of_payment") | select | join(" ") %}}
<style>
@page {{ size: 230mm 113mm; margin: 0; }}
.print-format {{ margin:0!important; padding:0!important; }}
.muntada-voucher {{ direction:rtl; font-family:"Traditional Arabic","Arial",sans-serif; color:#211f20;
    width:100%; height:110mm; position:relative; overflow:hidden; box-sizing:border-box; background:#fff; }}
.muntada-sidebar {{ position:absolute; top:0; right:0; bottom:0; width:12%; background:#000; color:#fff;
    display:flex; align-items:center; justify-content:center; writing-mode:vertical-rl; transform:rotate(180deg);
    font-size:19px; font-weight:800; text-align:center; padding:5mm 0; box-sizing:border-box; }}
.muntada-sidebar small {{ font-size:10px; font-weight:700; margin-top:7mm; }}
.muntada-logo {{ position:absolute; left:5%; right:auto!important; top:5mm; width:14%; height:28mm; object-fit:contain; }}
.muntada-heading {{ position:absolute; left:25%; top:6mm; width:58%; direction:rtl; text-align:center; }}
.muntada-basmala {{ font-size:10px; font-weight:700; line-height:1; margin-bottom:2mm; }}
.muntada-verse {{ font-size:19px; font-weight:700; white-space:nowrap; line-height:1.2; }}
.muntada-title {{ position:absolute; left:25%; top:34mm; width:61%; height:10mm; box-sizing:border-box;
    background:#000; color:#fff; font-size:23px; line-height:10mm; text-align:center; font-weight:700; }}
.muntada-amounts {{ position:absolute; left:5%; right:auto!important; top:35mm; direction:ltr; height:9mm; white-space:nowrap; }}
.amount-box {{ display:inline-block; border:1.5px solid #222; width:27mm; height:9mm; box-sizing:border-box;
    font-family:Arial,sans-serif; font-size:12px; line-height:8mm; font-weight:700; text-align:center; }}
.muntada-body {{ position:absolute; left:5%; right:16%; top:47mm; }}
.voucher-row {{ font-size:14px; font-weight:700; height:10mm; line-height:9mm; white-space:nowrap; }}
.dots {{ display:inline-block; border-bottom:1.4px dotted #333; min-width:57%; height:7mm;
    padding:0 1mm; font-size:13px; font-weight:500; line-height:7mm; vertical-align:bottom; overflow:hidden; }}
.phone-dots {{ min-width:20%; }} .short-dots {{ min-width:17%; }} .bank-dots {{ min-width:25%; }}
.check {{ display:inline-block; width:5mm; height:5mm; border:1.5px solid #222; margin:0 2mm;
    text-align:center; line-height:4mm; font-family:Arial; font-size:14px; vertical-align:middle; }}
.muntada-signatures {{ position:absolute; left:5%; right:16%; top:84mm; width:79%;
    border-top:2px solid #222; padding-top:1.5mm; table-layout:fixed; font-size:11px; font-weight:700; text-align:center; }}
.muntada-signatures td {{ vertical-align:top; width:33.33%; }}
.sign-line {{ border-bottom:1.4px dotted #333; height:5mm; margin:0 9mm; }}
.treasurer-signature {{ height:12mm; margin-top:-1mm; display:flex; align-items:center; justify-content:center; }}
.treasurer-signature img {{ display:block; max-width:25mm; max-height:12mm; width:auto; height:auto; object-fit:contain; }}
.muntada-date {{ position:absolute; right:16%; top:96mm; font-size:9px; font-weight:700; white-space:nowrap; }}
.date-separator {{ margin:0 4mm; color:#777; }}
.muntada-footer {{ position:absolute; left:5%; right:12%; bottom:2mm; border:1.5px solid #222;
    height:7mm; box-sizing:border-box; line-height:6mm; text-align:center; font-size:9px; font-weight:700; white-space:nowrap; }}
</style>
<div class="muntada-voucher">
  <div class="muntada-sidebar">جمعية المنتدى الطلابي<small>لبنان - علم وخبر ١٤٢٤/أ د</small></div>
  <img class="muntada-logo" src="/assets/accounting_custom/images/print_formats/al_muntada_tullabi_logo.png">
  <div class="muntada-heading"><div class="muntada-basmala">بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ</div><div class="muntada-verse">{verse}</div></div>
  <div class="muntada-amounts"><span class="amount-box">$ {{{{ "{{:,.2f}}".format(usd_amount or 0) }}}}</span><span class="amount-box">{{{{ "{{:,.0f}}".format(lbp_amount or 0) }}}} ل.ل</span></div>
  <div class="muntada-title">{title}</div>
  <div class="muntada-body">
    <div class="voucher-row">{party_label} <span class="dots">{{{{ parties }}}}</span> رقم الجوال: <span class="dots phone-dots"></span></div>
    <div class="voucher-row">مبلغ وقدره: <span class="dots">{{{{ doc.custom_amount_in_words_arabic or "" }}}}</span></div>
    <div class="voucher-row">نقدي <span class="check">{{% if "cash" in payment_modes|lower %}}✓{{% endif %}}</span> شيك رقم: <span class="dots short-dots"></span> مسحوب على بنك: <span class="dots bank-dots"></span></div>
    <div class="voucher-row">وذلك لحساب: <span class="dots">{{{{ doc.remarks or "" }}}}</span></div>
  </div>
  <table class="muntada-signatures"><tr>{signatures}</tr></table>
  {date_line}
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
	html = html.replace(
		"{{ donor_phone }}",
		'{{ frappe.db.get_value("Branch", doc.custom_branch, "custom_branch_name_arabic") or doc.custom_branch or "" }}',
		1,
	)
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
	html = html.replace(
		"{{ donor_phone }}",
		'{{ frappe.db.get_value("Branch", doc.custom_branch, "custom_branch_name_arabic") or doc.custom_branch or "" }}',
		1,
	)
	html = html.replace("وذلك لحساب:", "وذلك عن:", 1)
	return html



PAYSLIP_CSS = r"""
<style>
.print-heading{display:none!important}.print-format{padding:0!important;margin:0!important}
.ps{font-family:Arial,"Noto Naskh Arabic",sans-serif;color:#172033;direction:rtl;border:1px solid #98a2b3;border-radius:10px;overflow:hidden;background:#fff}.ps *{box-sizing:border-box}.ps-head{padding:16px 18px;background:#f8fafc;border-bottom:3px solid #7f1d1d;display:flex;justify-content:space-between;align-items:center}.ps-title{color:#8b1111;font-size:24px;font-weight:800}.ps-period{text-align:left;direction:ltr;font-size:12px;color:#475467}.ps-person{padding:12px 18px;display:grid;grid-template-columns:2fr 1fr;gap:10px;border-bottom:1px solid #d0d5dd}.ps-label{font-size:10px;color:#667085;margin-bottom:3px}.ps-value{font-size:14px;font-weight:700}.ps-body{padding:12px 18px}.ps-columns{display:grid;grid-template-columns:1fr 1fr;gap:14px}.ps-box{border:1px solid #d0d5dd;border-radius:7px;overflow:hidden}.ps-box-title{padding:7px 10px;background:#f2f4f7;font-size:13px;font-weight:800}.ps-row{display:flex;justify-content:space-between;gap:8px;padding:6px 10px;border-top:1px solid #eaecf0;font-size:12px}.ps-total{font-weight:800;background:#f9fafb}.ps-reasons{margin-top:8px;padding:7px 10px;background:#fff7ed;border:1px solid #fed7aa;border-radius:7px;font-size:10px;line-height:1.5;white-space:pre-line}.ps-reasons b{color:#9a3412}.ps-net{margin-top:12px;border:2px solid #157347;background:#ecfdf3;border-radius:8px;padding:10px 12px;display:flex;justify-content:space-between;font-size:17px;font-weight:800}.ps-declaration{margin-top:12px;padding:9px 11px;border:1px dashed #98a2b3;border-radius:7px;font-size:11px;line-height:1.7}.ps-sign{display:grid;grid-template-columns:1fr 1fr;gap:25px;margin-top:18px;font-size:11px}.ps-sign div{padding-top:22px;border-top:1px solid #667085}.ps-foot{padding:7px 18px;background:#f8fafc;border-top:1px solid #eaecf0;color:#667085;font-size:9px;direction:ltr;text-align:center}
@media print{.ps{page-break-inside:avoid;break-inside:avoid}.print-format{background:#fff!important}}
</style>
"""

PAYSLIP_CARD = r"""
<div class="ps">
 <div class="ps-head"><div><div class="ps-title">وثيقة استلام راتب</div><div class="ps-label">Salary Receipt</div></div><div class="ps-period"><b>{{ frappe.utils.formatdate(slip.start_date, "MMMM yyyy") }}</b><br>{{ frappe.utils.formatdate(slip.start_date) }} — {{ frappe.utils.formatdate(slip.end_date) }}</div></div>
 <div class="ps-person"><div><div class="ps-label">الاسم / Employee</div><div class="ps-value">{{ slip.employee_name_arabic or slip.employee_name }}</div></div><div><div class="ps-label">المسمى الوظيفي / Designation</div><div class="ps-value">{{ slip.designation or "—" }}</div></div></div>
 <div class="ps-body"><div class="ps-columns">
  <div class="ps-box"><div class="ps-box-title">الراتب والإضافات / Earnings</div><div class="ps-row"><span>الراتب الأساسي</span><b>{{ "{:,.0f}".format(slip.basic_salary or 0) }}</b></div><div class="ps-row"><span>بدل المواصلات</span><b>{{ "{:,.0f}".format(slip.transportation or 0) }}</b></div><div class="ps-row"><span>الإعانة العائلية</span><b>{{ "{:,.0f}".format(slip.family_allowance or 0) }}</b></div>{% if slip.other_earnings %}<div class="ps-row"><span>إضافات أخرى</span><b>{{ "{:,.0f}".format(slip.other_earnings) }}</b></div>{% endif %}<div class="ps-row ps-total"><span>الإجمالي</span><b>{{ "{:,.0f}".format(slip.gross_pay or 0) }} {{ slip.currency }}</b></div></div>
  <div class="ps-box"><div class="ps-box-title">الخصومات / Deductions</div><div class="ps-row"><span>الضرائب</span><b>{{ "{:,.0f}".format(slip.tax_deduction or 0) }}</b></div><div class="ps-row"><span>سلفة على الراتب</span><b>{{ "{:,.0f}".format(slip.advance_deduction or 0) }}</b></div><div class="ps-row"><span>خصومات أخرى</span><b>{{ "{:,.0f}".format(slip.other_deduction or 0) }}</b></div><div class="ps-row ps-total"><span>إجمالي الخصومات</span><b>{{ "{:,.0f}".format(slip.total_deduction or 0) }} {{ slip.currency }}</b></div></div>
 </div>{% if slip.deduction_reasons %}<div class="ps-reasons"><b>أسباب الخصومات / Deduction Reasons:</b><br>{{ slip.deduction_reasons }}</div>{% endif %}<div class="ps-net"><span>صافي المبلغ المدفوع / Net Pay</span><span>{{ "{:,.0f}".format(slip.net_pay or 0) }} {{ slip.currency }}</span></div>
 <div class="ps-declaration">بإمضائي على هذه الوثيقة، أقرّ باستلام راتبي عن الشهر المذكور أعلاه بقيمة صافي المبلغ المبين.</div><div class="ps-sign"><div>توقيع الموظف</div><div>التاريخ</div></div></div>
 <div class="ps-foot">{{ slip.name }}</div>
</div>
"""


def _individual_payslip_html():
	return PAYSLIP_CSS + "{% set slip = doc %}" + PAYSLIP_CARD


def _batch_payslip_html(per_page):
	columns = 1 if per_page == 1 else 2
	rows = 1 if per_page == 1 else per_page // 2
	gap = "0" if per_page == 1 else ("6mm" if per_page == 6 else "8mm")
	if per_page == 1:
		card_css = ""
	elif per_page == 4:
		card_css = """
.batch-grid .ps{height:100%;font-size:13px;display:flex;flex-direction:column}
.batch-grid .ps-head{padding:12px 14px;border-bottom-width:3px}.batch-grid .ps-title{font-size:24px}.batch-grid .ps-period{font-size:12px;line-height:1.5}.batch-grid .ps-person{padding:10px 14px;gap:9px}.batch-grid .ps-label{font-size:11px}.batch-grid .ps-value{font-size:14px}.batch-grid .ps-body{padding:10px 12px;flex:1;display:flex;flex-direction:column;gap:8px}.batch-grid .ps-columns{gap:9px}.batch-grid .ps-box-title{padding:7px 8px;font-size:13px}.batch-grid .ps-row{padding:6px 8px;font-size:12px}.batch-grid .ps-reasons{margin-top:0;font-size:10px;padding:6px 8px}.batch-grid .ps-net{margin-top:0;padding:9px 10px;font-size:15px}.batch-grid .ps-declaration{margin-top:0;padding:8px;font-size:11px;line-height:1.5}.batch-grid .ps-sign{margin-top:auto;gap:18px;font-size:12px}.batch-grid .ps-sign div{padding-top:22px}.batch-grid .ps-foot{padding:5px 10px;font-size:9px}
"""
	else:
		card_css = """
.batch-grid .ps{height:100%;font-size:8px;display:flex;flex-direction:column}
.batch-grid .ps-head{padding:7px 9px;border-bottom-width:2px}.batch-grid .ps-title{font-size:14px}.batch-grid .ps-period{font-size:8px}.batch-grid .ps-person{padding:6px 9px;gap:5px}.batch-grid .ps-label{font-size:7px}.batch-grid .ps-value{font-size:9px}.batch-grid .ps-body{padding:6px 9px;flex:1;display:flex;flex-direction:column}.batch-grid .ps-columns{gap:6px}.batch-grid .ps-box-title{padding:3px 5px;font-size:8px}.batch-grid .ps-row{padding:2px 5px;font-size:7.5px}.batch-grid .ps-reasons{margin-top:4px;padding:3px 5px;font-size:6.5px;line-height:1.2}.batch-grid .ps-net{margin-top:5px;padding:4px 6px;font-size:9px}.batch-grid .ps-declaration{margin-top:5px;padding:3px 5px;font-size:7px;line-height:1.35}.batch-grid .ps-sign{margin-top:auto;gap:12px;font-size:7px}.batch-grid .ps-sign div{padding-top:10px}.batch-grid .ps-foot{padding:2px 8px;font-size:6px}
"""
	layout_css = f"""
.batch-grid{{display:grid;grid-template-columns:repeat({columns},1fr);grid-template-rows:repeat({rows},1fr);gap:{gap};height:280mm;page-break-after:always;break-after:page}}
.batch-grid:last-of-type{{page-break-after:auto;break-after:auto}}
.batch-grid>.ps{{min-height:0}}
{card_css}
@page{{size:A4 portrait;margin:7mm}}
"""
	return PAYSLIP_CSS + f"""
<style>
{layout_css}
</style>
{{% for employee_group in doc.employees|groupby("employee") %}}
 {{% if loop.index0 % {per_page} == 0 %}}<div class="batch-grid">{{% endif %}}
 {{% set payslip_name = frappe.db.get_value("Employee Consolidated Payslip", {{"employee": employee_group.grouper, "start_date": doc.start_date, "end_date": doc.end_date}}, "name") %}}
 {{% if payslip_name %}}{{% set slip = frappe.get_doc("Employee Consolidated Payslip", payslip_name) %}}{PAYSLIP_CARD}{{% endif %}}
 {{% if loop.index % {per_page} == 0 or loop.last %}}</div>{{% endif %}}
{{% endfor %}}"""


def ensure_consolidated_payslip_print_format():
	if frappe.db.exists("Print Format", "Employee Consolidated Payslip"):
		frappe.db.set_value("Print Format", "Employee Consolidated Payslip", "disabled", 1, update_modified=False)
	formats = {
		"Employee Payslip - Professional": ("Employee Consolidated Payslip", _individual_payslip_html()),
		"Payroll Payslips - 1 per A4": ("Multi Company Payroll Run", _batch_payslip_html(1)),
		"Payroll Payslips - 4 per A4": ("Multi Company Payroll Run", _batch_payslip_html(4)),
		"Payroll Payslips - 6 per A4": ("Multi Company Payroll Run", _batch_payslip_html(6)),
	}
	for name, (doctype, html) in formats.items():
		values = {"doc_type": doctype, "module": "Accounting Custom", "standard": "No", "custom_format": 1, "disabled": 0, "print_format_type": "Jinja", "html": html, "margin_top": 7, "margin_bottom": 7, "margin_left": 7, "margin_right": 7}
		if frappe.db.exists("Print Format", name):
			frappe.db.set_value("Print Format", name, values, update_modified=False)
		else:
			frappe.get_doc({"doctype": "Print Format", "name": name, **values}).insert(ignore_permissions=True)
