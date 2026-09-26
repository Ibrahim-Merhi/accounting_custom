frappe.ui.form.on("Multi Company Payroll Run", {
	setup(frm) {
		frm.set_query("payroll_payable_account", "companies", (_doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return {filters: {company: row.company, is_group: 0, disabled: 0, account_type: ""}};
		});
	},
	refresh(frm) {
		if (frm.is_new()) return;
		if (!frm.doc.companies?.some((row) => row.payroll_entry)) {
			frm.add_custom_button(__("Get Employees"), () => run_action(frm, "get_employees", __("Loading employees and salary allocations...")));
		}
		if (frm.doc.status === "Employees Loaded") {
			frm.add_custom_button(__("Create Company Payroll Entries"), () => run_action(frm, "create_payroll_entries", __("Creating company Payroll Entries...")));
		}
		if (frm.doc.status === "Payroll Entries Created") {
			frm.add_custom_button(__("Create Salary Slips"), () => run_action(frm, "create_salary_slips", __("Creating Salary Slips...")));
		}
	},
});

function run_action(frm, method, message) {
	frm.call({method, freeze: true, freeze_message: message}).then(() => frm.reload_doc());
}
