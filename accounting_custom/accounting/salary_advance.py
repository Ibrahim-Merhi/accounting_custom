from calendar import monthrange

import erpnext
import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate

from accounting_custom.accounting.employee_profile import get_payroll_employee


def _deduction_component_for_account(company, advance_account):
    if not company or not advance_account:
        return None
    components = frappe.get_all(
        "Salary Component Account",
        filters={"company": company, "account": advance_account},
        pluck="parent",
    )
    for component in components:
        if frappe.db.get_value("Salary Component", component, "type") == "Deduction":
            return component
    return None


@frappe.whitelist()
def get_salary_advance_defaults(employee_profile, company=None):
    identities = frappe.get_all(
        "Employee",
        filters={"custom_master_employee": employee_profile, "status": "Active"},
        fields=["name", "company"],
        order_by="company asc",
    )
    if company:
        identities = [row for row in identities if row.company == company]
    options = []
    for identity in identities:
        advance_account, currency = frappe.db.get_value(
            "Company", identity.company,
            ["default_employee_advance_account", "default_currency"],
        ) or (None, None)
        options.append({
            "employee": identity.name,
            "company": identity.company,
            "advance_account": advance_account,
            "currency": currency,
            "cost_center": erpnext.get_default_cost_center(identity.company),
            "deduction_component": _deduction_component_for_account(identity.company, advance_account),
        })
    return options


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
    default_account = frappe.db.get_value("Company", doc.company, "default_employee_advance_account")
    doc.advance_account = doc.get("advance_account") or default_account
    if not doc.advance_account:
        frappe.throw(_("Select an Employee Advance Account for company {0}.").format(doc.company))
    account = frappe.db.get_value(
        "Account", doc.advance_account, ["company", "root_type", "is_group", "disabled"], as_dict=True
    )
    if not account or account.company != doc.company or account.root_type != "Asset" or account.is_group or account.disabled:
        frappe.throw(_("Select an enabled Asset ledger belonging to company {0}.").format(doc.company))
    if not doc.get("custom_advance_cost_center"):
        frappe.throw(_("Select an Advance Cost Center."))
    cost_center = frappe.db.get_value(
        "Cost Center", doc.custom_advance_cost_center, ["company", "is_group", "disabled"], as_dict=True
    )
    if not cost_center or cost_center.company != doc.company or cost_center.is_group or cost_center.disabled:
        frappe.throw(_("Select an enabled Cost Center belonging to company {0}.").format(doc.company))
    if not doc.get("mode_of_payment"):
        frappe.throw(_("Select a Mode of Payment."))
    component = doc.get("custom_salary_deduction_component")
    component_account = frappe.db.get_value(
        "Salary Component Account",
        {"parent": component, "company": doc.company},
        "account",
    ) if component else None
    if (
        not component
        or frappe.db.get_value("Salary Component", component, "type") != "Deduction"
        or component_account != doc.advance_account
    ):
        component = _deduction_component_for_account(doc.company, doc.advance_account)
    if not component:
        frappe.throw(_("Configure a deduction Salary Component using Employee Advance account {0} for company {1}.").format(doc.advance_account, doc.company))
    doc.custom_salary_deduction_component = component
    monthly_amount = flt(doc.get("custom_monthly_installment"))
    if monthly_amount <= 0:
        monthly_amount = flt(doc.advance_amount) / months
    if abs(monthly_amount * months - flt(doc.advance_amount)) > 0.01:
        frappe.throw(_("Monthly Deduction Amount x Number of Months must equal the Amount Given."))
    doc.custom_repayment_start_date = get_first_day(doc.custom_repayment_start_date)
    doc.custom_monthly_installment = monthly_amount
    doc.purpose = doc.purpose or _("Salary Advance")


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

@frappe.whitelist()
def make_salary_advance_bank_entry(dt, dn):
    """Create the standard advance payment journal using its selected cost center."""
    from hrms.hr.doctype.employee_advance.employee_advance import make_bank_entry

    doc = frappe.get_doc(dt, dn)
    if not doc.get("custom_advance_cost_center"):
        frappe.throw(_("Select an Advance Cost Center before paying this advance."))
    journal = make_bank_entry(dt, dn)
    for row in journal.get("accounts") or []:
        row.cost_center = doc.custom_advance_cost_center
    return journal
