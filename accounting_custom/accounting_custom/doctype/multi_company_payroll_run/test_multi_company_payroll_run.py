from unittest.mock import patch

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
