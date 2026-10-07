from unittest import TestCase
import frappe

from accounting_custom.setup.print_formats import (
	_company_conditional_html,
	_donation_donor_display_html,
	_islam_forum_html,
	_muntada_voucher_html,
	_payment_html,
	_standard_company_html,
	_individual_payslip_html,
	_batch_payslip_html,
)


class TestMuntadaPrintFormats(TestCase):
	def test_payment_and_receipt_templates_render(self):
		doc = frappe._dict(
			company="Al Muntada Al Tullabi",
			posting_date="2026-09-19",
			custom_hijri_date="1448/4/8",
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
		self.assertIn("100.00", payment)
		self.assertIn("1,000,000", receipt)
		self.assertEqual(payment.count("فقط لا غير"), 1)
		self.assertIn("1448/4/8", payment)
		self.assertIn("2026-09-19", receipt)

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

	def test_payment_format_uses_arabic_branch_name(self):
		html = _payment_html("{{ donor_phone }}")

		self.assertIn("custom_branch_name_arabic", html)
		self.assertIn("doc.custom_branch", html)

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

	def test_donation_receipt_supports_anonymous_labels_and_professional_title(self):
		template = _donation_donor_display_html(
			'<span>{{ doc.donor_name or doc.donor or "" }}</span>'
		)
		male = frappe.render_template(template, {
			"doc": frappe._dict(is_anonymous_male=1, is_anonymous_female=0),
		})
		female = frappe.render_template(template, {
			"doc": frappe._dict(is_anonymous_male=0, is_anonymous_female=1),
		})

		self.assertIn("فاعل خير", male)
		self.assertIn("فاعلة خير", female)
		self.assertNotIn("فاعلة خير", male)
		self.assertIn("professional_title", template)


	def test_professional_payslip_has_requested_fields_without_removed_ids(self):
		doc = frappe._dict(
			name="CPS-TEST", employee_name="Test Employee",
			employee_name_arabic="محمد أحمد علي", designation="Accountant",
			start_date="2027-03-01", end_date="2027-03-31", currency="USD",
			basic_salary=500, transportation=100, family_allowance=50,
			other_earnings=0, gross_pay=650, tax_deduction=10,
			advance_deduction=40, other_deduction=0, total_deduction=50, net_pay=600,
			deduction_reasons="تأخير: 10 USD\nسلفة راتب: 40 USD",
		)
		html = frappe.render_template(_individual_payslip_html(), {"doc": doc})
		self.assertIn("وثيقة استلام راتب", html)
		self.assertIn("محمد أحمد علي", html)
		self.assertNotIn("Test Employee", html)
		self.assertIn("أسباب الخصومات", html)
		self.assertIn("تأخير: 10 USD", html)
		self.assertIn("600 USD", html)
		self.assertNotIn("MOF #", html)
		self.assertNotIn("NSSF", html)
		self.assertNotIn("رقم الموظف", html)

	def test_batch_payslip_formats_define_exact_page_break_density(self):
		one = _batch_payslip_html(1)
		four = _batch_payslip_html(4)
		six = _batch_payslip_html(6)
		self.assertIn("grid-template-columns:repeat(1,1fr)", one)
		self.assertIn("grid-template-rows:repeat(1,1fr)", one)
		self.assertIn("grid-template-columns:repeat(2,1fr)", four)
		self.assertIn("grid-template-rows:repeat(2,1fr)", four)
		self.assertIn("grid-template-rows:repeat(3,1fr)", six)
		self.assertIn("height:280mm", four)
		self.assertIn("font-size:24px", four)
		self.assertIn("font-size:15px", four)
		self.assertIn("margin-top:auto", four)
		self.assertIn("page-break-after:always", four)
		self.assertIn("loop.index % 4", four)
		self.assertIn("loop.index % 6", six)
		self.assertIn('groupby("employee")', four)
		self.assertIn("A4 portrait", six)
		rendered = frappe.render_template(four, {"doc": frappe._dict(employees=[], start_date="2027-03-01", end_date="2027-03-31")})
		self.assertIn("batch-grid", rendered)
