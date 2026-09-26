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
		frm.toggle_display("cost_center", !managed);
		frm.toggle_display("payment_account", !managed);
		frm.toggle_display("custom_bank_allocations_section", managed);
		frm.toggle_display("custom_bank_payment_allocations", managed);
		if (!managed) return;

		make_bank_allocation_full_width(frm);
		if (frm.doc.docstatus === 1 && !(frm.doc.custom_bank_payment_allocations || []).length && !frm.__loading_bank_allocations) {
			frm.__loading_bank_allocations = true;
			frm.call("get_bank_payment_allocation_defaults").then((response) => {
				for (const allocation of response.message || []) {
					const row = frm.add_child("custom_bank_payment_allocations");
					row.cost_center = allocation.cost_center;
					row.amount = allocation.amount;
				}
				frm.refresh_field("custom_bank_payment_allocations");
			}).finally(() => { frm.__loading_bank_allocations = false; });
		}
	},
});

frappe.ui.form.on("Payroll Bank Payment Allocation", {
	payment_account(frm) { sync_primary_payment_account(frm); },
	custom_bank_payment_allocations_remove(frm) { sync_primary_payment_account(frm); },
});

function make_bank_allocation_full_width(frm) {
	const field = frm.get_field("custom_bank_payment_allocations");
	field?.$wrapper.closest(".form-column").removeClass("col-sm-6").addClass("col-sm-12");
}

function sync_primary_payment_account(frm) {
	const first_account = (frm.doc.custom_bank_payment_allocations || []).find((row) => row.payment_account)?.payment_account || "";
	frm.set_value("payment_account", first_account);
}
