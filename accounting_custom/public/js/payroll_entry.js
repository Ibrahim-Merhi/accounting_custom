frappe.ui.form.on("Payroll Entry", {
	setup(frm) {
		frm.set_query("employee", "custom_manual_deductions", () => ({filters: {company: frm.doc.company, status: "Active"}}));
		frm.set_query("salary_component", "custom_manual_deductions", () => ({filters: {type: "Deduction", disabled: 0}}));
	},
});
