from unittest import TestCase
import frappe

from accounting_custom.setup.print_formats import (
	_company_conditional_html,
	_islam_forum_html,
	_muntada_voucher_html,
	_standard_company_html,
)


class TestMuntadaPrintFormats(TestCase):
	def test_payment_and_receipt_templates_render(self):
		doc = frappe._dict(
			company="Al Muntada Al Tullabi",
			posting_date="2026-09-19",
			remarks="Test remarks",
			custom_amount_in_words_arabic="مائة دولار فقط لا غير",
			currency_totals=[
				frappe._dict(currency="USD", total_debit=100),
				frappe._dict(currency="LBP", total_debit=1_000_000),
			],
			custom_accounting_rows_copy=[
				frappe._dict(party_name="Test Party", mode_of_payment="CASH USD"),
			],
		)

		payment = frappe.render_template(_muntada_voucher_html(True), {"doc": doc})
		receipt = frappe.render_template(_muntada_voucher_html(False), {"doc": doc})

		self.assertIn("سند صرف", payment)
		self.assertIn("يُصرف إلى:", payment)
		self.assertIn("سند قبض", receipt)
		self.assertIn("وصلنا من:", receipt)
		self.assertIn("Test Party", payment)
		self.assertIn("Test remarks", receipt)

	def test_single_format_selects_design_by_company(self):
		template = _company_conditional_html(
			"STANDARD DESIGN", "MUNTADA DESIGN", "ISLAM FORUM DESIGN"
		)

		muntada = frappe.render_template(
			template, {"doc": frappe._dict(company="Al Muntada Al Tullabi")}
		)
		standard = frappe.render_template(
			template, {"doc": frappe._dict(company="Itihad")}
		)
		islam_forum = frappe.render_template(
			template, {"doc": frappe._dict(company="Al Muntada Islam Forum")}
		)

		self.assertIn("MUNTADA DESIGN", muntada)
		self.assertNotIn("STANDARD DESIGN", muntada)
		self.assertIn("STANDARD DESIGN", standard)
		self.assertIn("ISLAM FORUM DESIGN", islam_forum)
		self.assertNotIn("STANDARD DESIGN", islam_forum)
		self.assertEqual(_standard_company_html(template), "STANDARD DESIGN")

	def test_islam_forum_keeps_layout_and_rebrands_organization(self):
		standard = """<div class="organization-name organization-layout-v2">
		<span class="organization-primary">Old Name</span></div>
		<img src="/old-logo.png" style="filter:grayscale(1)">
		<div>STANDARD BODY</div>"""

		html = _islam_forum_html(standard)

		self.assertIn("جمعية الثقافة والتوجيه الاجتماعي", html)
		self.assertIn("علم وخبر ٣٢٥ أ٫د", html)
		self.assertIn("al_muntada_islam_forum_grayscale.png", html)
		self.assertIn("STANDARD BODY", html)

	def test_donation_muntada_template_uses_donation_fields(self):
		doc = frappe._dict(
			company="Al Muntada Al Tullabi",
			posting_date="2026-09-19",
			donor="DON-0001",
			donor_name="Test Donor",
			remarks="Donation remarks",
			custom_amount_in_words_arabic="مائة دولار فقط لا غير",
			payments=[
				frappe._dict(currency="USD", donation_amount=100, mode_of_payment="CASH USD"),
			],
		)

		html = frappe.render_template(
			_muntada_voucher_html(payment=False, donation=True), {"doc": doc}
		)

		self.assertIn("Test Donor", html)
		self.assertIn("100.00", html)
