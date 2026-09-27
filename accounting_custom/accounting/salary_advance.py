from calendar import monthrange

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate

from accounting_custom.accounting.employee_profile import get_payroll_employee


def prepare_salary_advance(doc, method=None):
    if not doc.get("custom_salary_installment_plan"):
        return
    if not doc.get("custom_employee_profile"):
        frappe.throw(_("Select an Employee Profile for a salary installment plan."))
    payroll_employee = get_payroll_employee(doc.custom_employee_profile, doc.company)
    if not payroll_employee:
        frappe.throw(_("No company payroll identity exists for {0} in {1}.").format(doc.custom_employee_profile, doc.company))
    doc.employee = payroll_employee
    doc.repay_unclaimed_amount_from_salary = 1
    months = int(doc.get("custom_repayment_months") or 0)
    if months < 1:
        frappe.throw(_("Repayment Months must be at least 1."))
    if not doc.get("custom_repayment_start_date"):
        frappe.throw(_("Select a Repayment Start Month."))
    if not doc.get("custom_salary_deduction_component"):
        frappe.throw(_("Select a Salary Deduction Component."))
    if frappe.db.get_value("Salary Component", doc.custom_salary_deduction_component, "type") != "Deduction":
        frappe.throw(_("Salary Deduction Component must be a deduction."))
    component_account = frappe.db.get_value("Salary Component Account", {"parent": doc.custom_salary_deduction_component, "company": doc.company}, "account")
    if component_account != doc.advance_account:
        frappe.throw(_("The deduction component account for {0} must be the Employee Advance account {1}.").format(doc.company, doc.advance_account))
    doc.custom_repayment_start_date = get_first_day(doc.custom_repayment_start_date)
    doc.custom_monthly_installment = flt(doc.advance_amount) / months


def create_installment_schedule(doc, method=None):
    if not doc.get("custom_salary_installment_plan") or doc.docstatus != 1:
        return
    if frappe.db.exists("Additional Salary", {"ref_doctype": "Employee Advance", "ref_docname": doc.name, "docstatus": ["<", 2]}):
        return
    start = get_first_day(doc.custom_repayment_start_date)
    end = get_last_day(add_months(start, int(doc.custom_repayment_months) - 1))
    installment = frappe.get_doc({
        "doctype": "Additional Salary",
        "employee": doc.employee,
        "company": doc.company,
        "salary_component": doc.custom_salary_deduction_component,
        "amount": doc.custom_monthly_installment,
        "currency": doc.currency,
        "is_recurring": 1,
        "from_date": start,
        "to_date": end,
        "overwrite_salary_structure_amount": 0,
        "ref_doctype": "Employee Advance",
        "ref_docname": doc.name,
    })
    installment.insert(ignore_permissions=True)
    installment.submit()
    doc.db_set("custom_installment_schedule", installment.name, update_modified=False)


def cancel_installment_schedule(doc, method=None):
    name = doc.get("custom_installment_schedule")
    if not name or not frappe.db.exists("Additional Salary", name):
        return
    schedule = frappe.get_doc("Additional Salary", name)
    if schedule.docstatus == 1:
        schedule.cancel()


def ensure_paid_installment_schedules():
    for name in frappe.get_all("Employee Advance", filters={"docstatus": 1, "custom_salary_installment_plan": 1, "paid_amount": [">", 0]}, pluck="name"):
        create_installment_schedule(frappe.get_doc("Employee Advance", name))
