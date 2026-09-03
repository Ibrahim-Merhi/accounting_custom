from unittest import TestCase
from unittest.mock import call, patch

from accounting_custom.setup.metadata import PRINT_FORMATS, REPORTS, ensure_visible_metadata


class TestVisibleMetadata(TestCase):
	@patch("accounting_custom.setup.metadata.frappe.clear_cache")
	@patch("accounting_custom.setup.metadata.frappe.db.set_value")
	@patch("accounting_custom.setup.metadata.frappe.db.exists", return_value=True)
	def test_formats_and_reports_are_enabled_and_linked(self, _exists, set_value, clear_cache):
		ensure_visible_metadata()

		self.assertEqual(set_value.call_count, len(PRINT_FORMATS) + len(REPORTS))
		for name, doc_type in PRINT_FORMATS.items():
			self.assertIn(call(
				"Print Format", name,
				{"doc_type": doc_type, "module": "Accounting Custom", "disabled": 0},
				update_modified=False,
			), set_value.call_args_list)
		for name, ref_doctype in REPORTS.items():
			self.assertIn(call(
				"Report", name,
				{
					"report_name": name, "ref_doctype": ref_doctype,
					"module": "Accounting Custom", "report_type": "Script Report",
					"is_standard": "Yes", "disabled": 0,
				},
				update_modified=False,
			), set_value.call_args_list)
		clear_cache.assert_has_calls([call(doctype="Print Format"), call(doctype="Report")])
