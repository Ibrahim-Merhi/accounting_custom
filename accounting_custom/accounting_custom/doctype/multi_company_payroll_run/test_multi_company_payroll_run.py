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

    def test_manual_deduction_caps_full_payment_to_new_net_salary(self):
        run = frappe.get_doc({
            "doctype": "Multi Company Payroll Run",
            "payroll_month": "September",
            "payroll_year": 2026,
            "employees": [{
                "employee": "MASTER-1",
                "employee_name": "Employee",
                "company": "Itihad",
                "payroll_employee": "PAY-1",
                "gross_salary": 550,
                "previously_paid": 0,
                "pay_this_run": 550,
            }],
            "manual_deductions": [{
                "employee": "MASTER-1",
                "company": "Itihad",
                "payroll_employee": "PAY-1",
                "amount": 100,
            }],
        })
        with patch.object(MultiCompanyPayrollRun, "_scheduled_advance_deductions", return_value=0):
            run._refresh_employee_totals()
        row = run.employees[0]
        self.assertEqual(row.deductions, 100)
        self.assertEqual(row.net_salary, 450)
        self.assertEqual(row.pay_this_run, 450)
        self.assertEqual(row.deferred_amount, 0)

        run.set("manual_deductions", [])
        with patch.object(MultiCompanyPayrollRun, "_scheduled_advance_deductions", return_value=0):
            run._refresh_employee_totals()
        self.assertEqual(row.deductions, 0)
        self.assertEqual(row.net_salary, 550)
        self.assertEqual(row.pay_this_run, 550)
        self.assertEqual(row.deferred_amount, 0)

    def test_company_totals_follow_employee_changes(self):
        run = frappe.get_doc({
            "doctype": "Multi Company Payroll Run",
            "companies": [
                {"company": "Company A", "payroll_payable_account": "Payable A", "currency": "USD", "status": "Ready"},
                {"company": "Company B", "payroll_payable_account": "Payable B", "currency": "USD", "status": "Ready"},
            ],
            "employees": [
                {"employee": "MASTER-1", "company": "Company A", "payroll_employee": "PAY-1", "pay_this_run": 200},
                {"employee": "MASTER-2", "company": "Company A", "payroll_employee": "PAY-2", "pay_this_run": 450},
                {"employee": "MASTER-3", "company": "Company B", "payroll_employee": "PAY-3", "pay_this_run": 300},
            ],
        })
        run._refresh_company_totals()
        self.assertEqual([(row.company, row.employee_count, row.gross_salary) for row in run.companies], [
            ("Company A", 2, 650), ("Company B", 1, 300),
        ])

        run.set("employees", [row for row in run.employees if row.company == "Company A" and row.payroll_employee == "PAY-1"])
        run._refresh_company_totals()
        self.assertEqual(len(run.companies), 1)
        self.assertEqual(run.companies[0].company, "Company A")
        self.assertEqual(run.companies[0].employee_count, 1)
        self.assertEqual(run.companies[0].gross_salary, 200)
        self.assertEqual(run.companies[0].payroll_payable_account, "Payable A")

    def test_missing_payroll_entry_links_are_cleared_before_recreation(self):
        run = frappe.get_doc({
            "doctype": "Multi Company Payroll Run",
            "companies": [{"company": "Company", "payroll_entry": "PE-MISSING", "status": "Created"}],
            "employees": [{
                "employee": "MASTER-1", "company": "Company", "payroll_employee": "PAY-1",
                "source_payroll_entry": "PE-MISSING", "salary_slip": "SS-MISSING", "status": "Payment Ready",
            }],
        })
        with patch(
            "accounting_custom.accounting_custom.doctype.multi_company_payroll_run.multi_company_payroll_run.frappe.get_all",
            return_value=[],
        ):
            run._clear_missing_payroll_entry_links()
        self.assertIsNone(run.companies[0].payroll_entry)
        self.assertEqual(run.companies[0].status, "Ready")
        self.assertIsNone(run.employees[0].source_payroll_entry)
        self.assertIsNone(run.employees[0].salary_slip)
        self.assertEqual(run.employees[0].status, "Ready")

    def test_large_company_is_queued_instead_of_blocked(self):
        run = frappe.get_doc({
            "doctype": "Multi Company Payroll Run",
            "companies": [{"company": "Company", "payroll_entry": "PE-LARGE", "status": "Created"}],
        })
        entry = MagicMock()
        entry.docstatus = 0
        entry.employees = [frappe._dict(employee=f"EMP-{index}") for index in range(31)]
        with patch(
            "accounting_custom.accounting_custom.doctype.multi_company_payroll_run.multi_company_payroll_run.frappe.get_doc",
            return_value=entry,
        ):
            queued = run._process_company(run.companies[0])
        self.assertTrue(queued)
        self.assertEqual(run.companies[0].status, "Queued")
        entry.submit.assert_called_once()
        entry.submit_salary_slips.assert_not_called()

    def test_processing_run_enqueues_long_background_job_after_submit(self):
        run = frappe.get_doc({
            "doctype": "Multi Company Payroll Run", "name": "MCPR-LARGE", "status": "Processing",
        })
        with patch(
            "accounting_custom.accounting_custom.doctype.multi_company_payroll_run.multi_company_payroll_run.frappe.enqueue"
        ) as enqueue:
            run.on_submit()
        enqueue.assert_called_once()
        self.assertEqual(enqueue.call_args.kwargs["queue"], "long")
        self.assertEqual(enqueue.call_args.kwargs["timeout"], 3000)
        self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])
        self.assertEqual(enqueue.call_args.kwargs["payroll_run"], "MCPR-LARGE")

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

    def test_company_entry_names_keep_all_entries_without_duplicate_company_rows(self):
        run = frappe.get_doc({
            "doctype": "Multi Company Payroll Run",
            "companies": [{"company": "Company", "payroll_entry": "PE-NEW"}],
            "employees": [
                {"employee": "MASTER-1", "company": "Company", "payroll_employee": "PAY-1", "source_payroll_entry": "PE-OLD"},
                {"employee": "MASTER-2", "company": "Company", "payroll_employee": "PAY-2", "source_payroll_entry": "PE-NEW"},
                {"employee": "MASTER-3", "company": "Other", "payroll_employee": "PAY-3", "source_payroll_entry": "PE-OTHER"},
            ],
        })
        self.assertEqual(run._company_entry_names("Company", run.companies[0]), ["PE-NEW", "PE-OLD"])

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

    def test_advance_recovery_posts_payable_debit_and_advance_credit(self):
        entry = CustomPayrollEntry({"doctype": "Payroll Entry", "payroll_payable_account": "421 - Salaries Payable"})
        entry._advance_deduction_entries = [{
            "employee": "EMP-1", "account": "429 - Employee Advances", "cost_center": "CC-1",
            "amount": 40, "reference_name": "ADV-1",
        }]
        rows = []

        def add(account, cost_center, amount, _currencies, _company_currency, payable_amount,
                _dimensions, _precision, entry_type="credit", **kwargs):
            rows.append((account, cost_center, amount, entry_type, kwargs.get("party")))
            return payable_amount + amount if entry_type == "debit" else payable_amount - amount

        with patch.object(entry, "get_accounting_entries_and_payable_amount", side_effect=add):
            payable = entry.set_accounting_entries_for_advance_deductions([], [], "USD", [], 2, 500)

        self.assertEqual(payable, 500)
        self.assertEqual(rows[0], ("429 - Employee Advances", "CC-1", 40, "credit", "EMP-1"))
        self.assertEqual(rows[1], ("421 - Salaries Payable", "CC-1", 40, "debit", "EMP-1"))

    def test_advance_recovery_restores_gross_payable_credit(self):
        entry = CustomPayrollEntry({"doctype": "Payroll Entry", "payroll_payable_account": "421 - Salaries Payable"})
        entry._advance_deduction_entries = [{"employee": "EMP-1", "cost_center": "CC-1", "amount": 40}]
        calls = []
        with patch.object(entry, "_is_managed_payroll", return_value=True), patch.object(
            entry, "_get_managed_payable_rows", return_value=[frappe._dict(employee="EMP-1", cost_center="CC-1", amount=460)]
        ), patch.object(
            entry, "get_accounting_entries_and_payable_amount", side_effect=lambda *args, **kwargs: calls.append((args[0], args[2], kwargs.get("entry_type")))
        ):
            entry.set_payable_amount_against_payroll_payable_account([], [], "USD", [], 2, 500, entry.payroll_payable_account, False)

        self.assertEqual(calls, [
            ("421 - Salaries Payable", 460, "payable"),
            ("421 - Salaries Payable", 40, "payable"),
        ])
