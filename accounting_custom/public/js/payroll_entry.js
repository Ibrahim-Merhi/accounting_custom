frappe.ui.form.on("Payroll Entry", {
	setup(frm) {
		frm.set_query("employee", "custom_manual_deductions", () => ({filters: {company: frm.doc.company, status: "Active"}}));
		frm.set_query("salary_component", "custom_manual_deductions", () => ({filters: {type: "Deduction", disabled: 0}}));
		frm.set_query("payment_account", "custom_bank_payment_allocations", () => ({filters: {
			company: frm.doc.company, is_group: 0, disabled: 0,
			account_type: ["in", ["Bank", "Cash"]],
		}}));
		frm.set_query("cost_center", "custom_bank_payment_allocations", () => ({filters: {
			company: frm.doc.company, is_group: 0, disabled: 0,
		}}));
	},
	refresh(frm) {
		const managed = Boolean(frm.doc.custom_multi_company_payroll_run);
		frm.toggle_display("payment_account", !managed);
		frm.toggle_display("custom_bank_allocations_section", managed);
		frm.toggle_display("custom_bank_payment_allocations", managed);
	},
});

frappe.ui.form.on("Payroll Bank Payment Allocation", {
	payment_account(frm) { sync_primary_payment_account(frm); },
	custom_bank_payment_allocations_remove(frm) { sync_primary_payment_account(frm); },
});

function sync_primary_payment_account(frm) {
	const first_account = (frm.doc.custom_bank_payment_allocations || []).find((row) => row.payment_account)?.payment_account || "";
	frm.set_value("payment_account", first_account);
}
