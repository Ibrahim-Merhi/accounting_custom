from unittest import TestCase
from unittest.mock import call, patch

import frappe

from accounting_custom.setup.custom_fields import backfill_arabic_branch_names


class TestBranchSetup(TestCase):
	@patch("accounting_custom.setup.custom_fields.frappe.db.set_value")
	@patch("accounting_custom.setup.custom_fields.frappe.get_all")
	@patch("accounting_custom.setup.custom_fields.frappe.db.has_column", return_value=True)
	def test_backfill_translates_known_branch_parts(self, has_column, get_all, set_value):
		get_all.return_value = [
			frappe._dict(
				name="Beirut - Montada", branch="Beirut - Montada",
				custom_branch_name_arabic=None,
			),
			frappe._dict(
				name="Tripoli", branch="Tripoli",
				custom_branch_name_arabic="طرابلس الخاصة",
			),
		]

		backfill_arabic_branch_names()

		set_value.assert_has_calls([
			call(
				"Branch", "Beirut - Montada", "custom_branch_name_arabic",
				"بيروت - المنتدى", update_modified=False,
			),
		])
		self.assertEqual(set_value.call_count, 1)
