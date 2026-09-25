frappe.ui.form.on("Employee Salary Profile", {
	setup(frm) {
		for (const fieldname of ["basic_allocations", "transportation_allocations", "family_allowance_allocations"]) {
			frm.set_query("account", fieldname, (_doc, cdt, cdn) => {
				const row = locals[cdt][cdn];
				return {filters: row.company ? {company: row.company, is_group: 0, disabled: 0} : {name: ["=", ""]}};
			});
			frm.set_query("cost_center", fieldname, (_doc, cdt, cdn) => {
				const row = locals[cdt][cdn];
				return {filters: row.company ? {company: row.company, is_group: 0, disabled: 0} : {name: ["=", ""]}};
			});
		}
	},
	refresh(frm) {
		recalculate_all_allocations(frm);
		render_salary_revision_history(frm);
		if (frm.doc.employee) {
			frm.add_custom_button(__("Salary Revisions"), () => {
				frappe.set_route("List", "Employee Salary Revision", {employee: frm.doc.employee});
			});
		}
	},
	basic_allocations_remove(frm) { recalculate_all_allocations(frm); },
	transportation_allocations_remove(frm) { recalculate_all_allocations(frm); },
	family_allowance_allocations_remove(frm) { recalculate_all_allocations(frm); },
});

frappe.ui.form.on("Employee Salary Allocation", {
	amount(frm) {
		recalculate_all_allocations(frm);
	},
});

function allocation_configuration(table_field) {
	return {
		basic_allocations: {amount_field: "basic_salary"},
		transportation_allocations: {amount_field: "transportation"},
		family_allowance_allocations: {amount_field: "family_allowance"},
	}[table_field];
}

function recalculate_allocation_table(frm, table_field, amount_field) {
	const rows = frm.doc[table_field] || [];
	const total = flt(rows.reduce((sum, row) => sum + flt(row.amount), 0), 2);
	rows.forEach((row) => {
		const percentage = total > 0 ? flt(flt(row.amount) / total * 100, 6) : 0;
		if (flt(row.percentage, 6) !== percentage) {
			frappe.model.set_value(row.doctype, row.name, "percentage", percentage);
		}
	});
	if (flt(frm.doc[amount_field], 2) !== total) {
		frappe.model.set_value(frm.doctype, frm.docname, amount_field, total);
	}
	frm.refresh_field(table_field);
}

function recalculate_all_allocations(frm) {
	for (const table_field of ["basic_allocations", "transportation_allocations", "family_allowance_allocations"]) {
		const configuration = allocation_configuration(table_field);
		recalculate_allocation_table(frm, table_field, configuration.amount_field);
	}
	const total_salary = flt(frm.doc.basic_salary) + flt(frm.doc.transportation) + flt(frm.doc.family_allowance);
	if (flt(frm.doc.total_salary, 2) !== flt(total_salary, 2)) {
		frappe.model.set_value(frm.doctype, frm.docname, "total_salary", total_salary);
	}
}

function render_salary_revision_history(frm) {
	const field = frm.get_field("revision_history");
	if (!field || frm.is_new()) return;
	frappe.call({
		method: "accounting_custom.accounting.salary_profile.get_revision_history",
		args: {profile: frm.doc.name},
		callback: ({message}) => {
			const rows = message || [];
			const body = rows.map((row) => `<tr>
				<td><a href="/app/employee-salary-revision/${encodeURIComponent(row.name)}">${row.revision_number}</a></td>
				<td>${frappe.datetime.str_to_user(row.effective_from)}</td>
				<td>${row.effective_to ? frappe.datetime.str_to_user(row.effective_to) : __("Current")}</td>
				<td>${frappe.datetime.str_to_user(row.action_date)}</td>
				<td>${format_currency(row.basic_salary)}</td>
				<td>${format_currency(row.transportation)}</td>
				<td>${format_currency(row.family_allowance)}</td>
				<td class="font-weight-bold">${format_currency(row.total_salary)}</td>
				<td>${frappe.utils.escape_html(row.change_summary || "")}</td>
			</tr>`).join("");
			field.$wrapper.html(`<div class="table-responsive"><table class="table table-bordered table-hover">
				<thead><tr><th>${__("Revision")}</th><th>${__("Effective From")}</th><th>${__("Effective To")}</th><th>${__("Action Date")}</th><th>${__("Basic Salary")}</th><th>${__("Transportation")}</th><th>${__("Family Allowance")}</th><th>${__("Total")}</th><th>${__("Changes")}</th></tr></thead>
				<tbody>${body || `<tr><td colspan="9" class="text-muted text-center">${__("No salary revisions yet.")}</td></tr>`}</tbody></table></div>`);
		},
	});
}
