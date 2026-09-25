frappe.ui.form.on("Employee", {
	setup(frm) {
		set_employee_accounting_queries(frm);
	},
	company(frm) {
		set_employee_accounting_queries(frm);
	},
});

function set_employee_accounting_queries(frm) {
	frm.set_query("branch", "custom_branches", () => ({
		filters: frm.doc.company ? {custom_company: frm.doc.company} : {name: ["=", ""]},
	}));
	frm.set_query("account", "custom_salary_accounts", () => ({
		filters: frm.doc.company ? {company: frm.doc.company, is_group: 0, disabled: 0} : {name: ["=", ""]},
	}));
}
