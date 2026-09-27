from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.accounting_custom.doctype.multi_company_payroll_run.multi_company_payroll_run import (
    MultiCompanyPayrollRun,
)
from accounting_custom.overrides.payroll_entry import CustomPayrollEntry


class TestMultiCompanyPayrollRun(FrappeTestCase):
    def test_month_and_year_define_period(self):
        run = frappe.get_doc({
            "doctype": "Multi Company Payroll Run",
            "payroll_month": "February",
            "payroll_year": 2028,
        })
        run._set_month_period()
        self.assertEqual(str(run.start_date), "2028-02-01")
        self.assertEqual(str(run.end_date), "2028-02-29")
        self.assertEqual(run.payroll_frequency, "Monthly")

    def test_partial_payment_calculates_deferred_balance(self):
        run = frappe.get_doc({
            "doctype": "Multi Company Payroll Run",
            "payroll_month": "January",
            "payroll_year": 2027,
            "employees": [{
                "employee": "MASTER-1",
                "employee_name": "Employee",
                "company": "Company",
                "payroll_employee": "PAY-1",
                "gross_salary": 500,
                "previously_paid": 100,
                "pay_this_run": 150,
            }],
        })
        with patch.object(MultiCompanyPayrollRun, "_scheduled_advance_deductions", return_value=40):
            run._refresh_employee_totals()
        row = run.employees[0]
        self.assertEqual(row.deductions, 40)
        self.assertEqual(row.net_salary, 460)
        self.assertEqual(row.deferred_amount, 210)

    def test_company_with_all_rows_removed_is_deferred(self):
        run = frappe.get_doc({
            "doctype": "Multi Company Payroll Run",
            "companies": [{"company": "Company", "status": "Ready"}],
        })
        run._process_company(run.companies[0])
        self.assertEqual(run.companies[0].status, "Deferred")

    def test_cancelling_release_run_does_not_cancel_original_payroll(self):
        run = frappe.get_doc({
            "doctype": "Multi Company Payroll Run",
            "name": "MCPR-RELEASE",
            "companies": [{"company": "Company", "payroll_entry": "PE-ORIGINAL"}],
        })
        entry = MagicMock()
        entry.docstatus = 1
        entry.get.side_effect = lambda key: {
            "custom_multi_company_payroll_run": "MCPR-ORIGINAL",
            "custom_payment_payroll_run": "MCPR-RELEASE",
        }.get(key)
        with patch("accounting_custom.accounting_custom.doctype.multi_company_payroll_run.multi_company_payroll_run.frappe.db.exists", side_effect=lambda doctype, *args, **kwargs: doctype == "Payroll Entry"), patch(
            "accounting_custom.accounting_custom.doctype.multi_company_payroll_run.multi_company_payroll_run.frappe.get_doc", return_value=entry
        ), patch.object(run, "db_set"):
            run.on_cancel()
        entry.cancel.assert_not_called()
        entry.save.assert_called_once()
        self.assertIsNone(entry.custom_payment_payroll_run)

    def test_outstanding_payable_subtracts_prior_bank_payments(self):
        entry = CustomPayrollEntry({"doctype": "Payroll Entry", "name": "PE-1", "payroll_payable_account": "Payable"})
        payable = [frappe._dict({"employee": "EMP-1", "cost_center": "CC-1", "amount": 500})]
        paid = [frappe._dict({"employee": "EMP-1", "cost_center": "CC-1", "amount": 200})]
        with patch.object(CustomPayrollEntry, "_get_managed_payable_rows", return_value=payable), patch(
            "accounting_custom.overrides.payroll_entry.frappe.db.sql", return_value=paid
        ):
            rows = entry.get_outstanding_payable_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].amount, 300, repr(rows))
