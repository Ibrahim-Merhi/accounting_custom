frappe.ui.form.on("Employee", {
	setup(frm) {
		set_employee_accounting_queries(frm);
	},
});

frappe.ui.form.on("Employee Branch Assignment", {
	company(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "branch", null);
		frappe.model.set_value(cdt, cdn, "department", null);
		frappe.model.set_value(cdt, cdn, "account", null);
	},
});

function assignment_company(cdt, cdn) {
	return locals[cdt][cdn].company;
}

function company_filter(cdt, cdn, extra = {}) {
	const company = assignment_company(cdt, cdn);
	return company ? {company, ...extra} : {name: ["=", ""]};
}

function set_employee_accounting_queries(frm) {
	frm.set_query("branch", "custom_branches", (_doc, cdt, cdn) => {
		const company = assignment_company(cdt, cdn);
		return {filters: company ? {custom_company: company} : {name: ["=", ""]}};
	});
	frm.set_query("department", "custom_branches", (_doc, cdt, cdn) => ({
		filters: company_filter(cdt, cdn),
	}));
	frm.set_query("account", "custom_branches", (_doc, cdt, cdn) => ({
		filters: company_filter(cdt, cdn, {is_group: 0, disabled: 0}),
	}));
}
