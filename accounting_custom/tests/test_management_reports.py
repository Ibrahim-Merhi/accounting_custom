from unittest import TestCase
from unittest.mock import patch

from accounting_custom.reporting.management_reports import donor_history


class TestManagementReports(TestCase):
	@patch("accounting_custom.reporting.management_reports.frappe.db.sql", return_value=[])
	def test_donor_history_uses_donor_party_ledger_rows(self, sql):
		columns, _data = donor_history({
			"company": "Itihad", "from_date": "2026-01-01",
			"to_date": "2026-12-31", "donor": "DON-0001",
		})

		query, filters = sql.call_args.args[:2]
		self.assertIn("from `tabGL Entry` gle", query)
		self.assertIn("gle.party_type='Donor'", query)
		self.assertIn("gle.party=%(donor)s", query)
		self.assertIn("not exists", query)
		self.assertIn("gle.credit_in_account_currency", query)
		self.assertNotIn("tabDonation Payment Detail", query)
		self.assertEqual(filters["donor"], "DON-0001")
		self.assertIn("voucher_no", {column["fieldname"] for column in columns})
