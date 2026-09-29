from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.accounting.salary_advance import (
    make_salary_advance_bank_entry,
    prepare_salary_advance,
)


class TestSalaryAdvanceInstallments(FrappeTestCase):
    @patch("accounting_custom.accounting.salary_advance.get_payroll_employee", return_value="PAY-EMP-1")
    @patch("accounting_custom.accounting.salary_advance.frappe.db.get_value")
    def test_advance_is_split_into_selected_number_of_months(self, get_value, _get_employee):
        def value(doctype, filters, field, **kwargs):
            if doctype == "Account":
                return frappe._dict(company="Company", root_type="Asset", is_group=0, disabled=0)
            if doctype == "Cost Center":
                return frappe._dict(company="Company", is_group=0, disabled=0)
            if doctype == "Salary Component":
                return "Deduction"
            if doctype == "Salary Component Account":
                return "Employee Advance - CO"
            return None

        get_value.side_effect = value
        advance = frappe._dict({
            "custom_salary_installment_plan": 1,
            "custom_employee_profile": "EMP-1",
            "company": "Company",
            "advance_amount": 200,
            "advance_account": "Employee Advance - CO",
            "custom_advance_cost_center": "Main - CO",
            "mode_of_payment": "Cash",
            "custom_repayment_months": 5,
            "custom_repayment_start_date": "2027-04-18",
            "custom_salary_deduction_component": "Salary Advance Deduction",
        })
        prepare_salary_advance(advance)
        self.assertEqual(advance.employee, "PAY-EMP-1")
        self.assertEqual(advance.custom_monthly_installment, 40)
        self.assertEqual(str(advance.custom_repayment_start_date), "2027-04-01")
        self.assertEqual(advance.repay_unclaimed_amount_from_salary, 1)

    @patch("hrms.hr.doctype.employee_advance.employee_advance.make_bank_entry")
    @patch("accounting_custom.accounting.salary_advance.frappe.get_doc")
    def test_payment_journal_uses_selected_cost_center(self, get_doc, make_bank_entry):
        get_doc.return_value = frappe._dict(custom_advance_cost_center="Projects - CO")
        make_bank_entry.return_value = frappe._dict(accounts=[frappe._dict(), frappe._dict()])

        journal = make_salary_advance_bank_entry("Employee Advance", "ADV-1")

        self.assertEqual([row.cost_center for row in journal.accounts], ["Projects - CO", "Projects - CO"])
