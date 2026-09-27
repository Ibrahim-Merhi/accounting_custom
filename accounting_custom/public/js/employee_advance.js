frappe.ui.form.on("Employee Advance", {
    setup(frm) {
        frm.set_query("custom_employee_profile", () => ({filters: {custom_is_payroll_identity: 0}}));
        frm.set_query("custom_salary_deduction_component", () => ({filters: {type: "Deduction", disabled: 0}}));
    },
    refresh(frm) {
        const planned = Boolean(frm.doc.custom_salary_installment_plan);
        frm.toggle_display("employee", !planned);
        if (planned && frm.doc.custom_monthly_installment) {
            frm.dashboard.set_headline_alert(__("{0} will be deducted monthly for {1} month(s).", [format_currency(frm.doc.custom_monthly_installment, frm.doc.currency), frm.doc.custom_repayment_months]), "blue");
        }
    },
    custom_salary_installment_plan(frm) { frm.trigger("refresh"); },
    advance_amount(frm) { calculate_installment(frm); },
    custom_repayment_months(frm) { calculate_installment(frm); },
});
function calculate_installment(frm) {
    const months = cint(frm.doc.custom_repayment_months);
    frm.set_value("custom_monthly_installment", months > 0 ? flt(frm.doc.advance_amount) / months : 0);
}
