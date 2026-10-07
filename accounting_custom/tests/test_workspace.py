from unittest import TestCase

from accounting_custom.setup.workspace import (
	ACCOUNT_COST_CENTER_REPORT,
	ANALYTICAL_TRIAL_BALANCE,
	_insert_custom_report_links,
)


class TestAccountingWorkspace(TestCase):
	def test_custom_reports_section_contains_both_required_reports(self):
		links = _insert_custom_report_links([
			{"type": "Card Break", "label": "Custom Reports"},
			{"type": "Card Break", "label": "Another Section"},
		])

		self.assertEqual(
			[row.get("link_to") for row in links[1:3]],
			[ACCOUNT_COST_CENTER_REPORT, ANALYTICAL_TRIAL_BALANCE],
		)
		self.assertTrue(all(row.get("is_query_report") for row in links[1:3]))
