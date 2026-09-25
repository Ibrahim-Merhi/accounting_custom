frappe.ui.form.on("Employee", {
	setup(frm) {
		set_employee_position_queries(frm);
	},
	refresh(frm) {
		render_secure_salary_profile(frm);
	},
});

frappe.ui.form.on("Employee Branch Assignment", {
	custom_branches_add(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.from_date) {
			frappe.model.set_value(cdt, cdn, "from_date", frm.doc.date_of_joining || frappe.datetime.get_today());
		}
	},
	company(_frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "branch", null);
		frappe.model.set_value(cdt, cdn, "department", null);
	},
	left_position(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.left_position || row.leaving_date) return;
		frappe.prompt(
			[{fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today()}],
			(values) => {
				frappe.model.set_value(cdt, cdn, "leaving_date", values.to_date).then(() => frm.save());
			},
			__("Leave Position"),
			__("Move to Past Positions")
		);
	},
});

function position_company(cdt, cdn) {
	return locals[cdt][cdn].company;
}

function company_filter(cdt, cdn) {
	const company = position_company(cdt, cdn);
	return company ? {company} : {name: ["=", ""]};
}

function set_employee_position_queries(frm) {
	frm.set_query("branch", "custom_branches", (_doc, cdt, cdn) => {
		const company = position_company(cdt, cdn);
		return {filters: company ? {custom_company: company} : {name: ["=", ""]}};
	});
	frm.set_query("department", "custom_branches", (_doc, cdt, cdn) => ({filters: company_filter(cdt, cdn)}));
}

function render_secure_salary_profile(frm) {
	const can_access = frappe.user_roles.includes("Accounts Manager");
	frm.toggle_display("salary_information", can_access);
	if (!can_access || frm.is_new()) return;
	frappe.call({
		method: "accounting_custom.accounting.salary_profile.get_salary_profile_summary",
		args: {employee: frm.doc.name},
		callback: ({message}) => {
			const profile = message || {exists: false};
			const field = frm.get_field("custom_secure_salary_profile");
			if (!field) return;
			const action = profile.exists
				? `<button class="btn btn-primary btn-sm open-salary-profile">${__("Open Salary Profile")}</button>`
				: `<button class="btn btn-primary btn-sm create-salary-profile">${__("Create Salary Profile")}</button>`;
			field.$wrapper.html(`<div class="frappe-card p-4">
				<h4>${__("Protected Salary Profile")}</h4>
				${profile.exists ? `<div class="row"><div class="col-sm-3"><small>${__("Effective From")}</small><div>${frappe.datetime.str_to_user(profile.effective_date)}</div></div><div class="col-sm-3"><small>${__("Total Salary")}</small><div class="font-weight-bold">${format_currency(profile.total_salary)}</div></div><div class="col-sm-3"><small>${__("Revisions")}</small><div>${profile.revision_count}</div></div></div>` : `<p class="text-muted">${__("No salary profile has been created for this employee.")}</p>`}
				${render_salary_slips(profile.salary_slips)}
				<div class="mt-3">${action}</div></div>`);
			field.$wrapper.find(".open-salary-profile").on("click", () => frappe.set_route("Form", "Employee Salary Profile", profile.name));
			field.$wrapper.find(".create-salary-profile").on("click", () => frappe.new_doc("Employee Salary Profile", {employee: frm.doc.name}));
		},
	});
}

function render_salary_slips(slips) {
	if (!slips || !slips.length) return "";
	const rows = slips.map((slip) => `<tr>
		<td><a href="/app/salary-slip/${encodeURIComponent(slip.name)}">${frappe.utils.escape_html(slip.name)}</a></td>
		<td>${frappe.utils.escape_html(slip.company)}</td>
		<td>${frappe.datetime.str_to_user(slip.start_date)} – ${frappe.datetime.str_to_user(slip.end_date)}</td>
		<td>${format_currency(slip.net_pay, slip.currency)}</td>
		<td><a class="btn btn-xs btn-default" target="_blank" href="/printview?doctype=Salary%20Slip&name=${encodeURIComponent(slip.name)}&trigger_print=1">${__("Print")}</a></td>
	</tr>`).join("");
	return `<div class="mt-4"><h5>${__("Recent Salary Slips")}</h5><div class="table-responsive"><table class="table table-bordered">
		<thead><tr><th>${__("Salary Slip")}</th><th>${__("Company")}</th><th>${__("Period")}</th><th>${__("Net Pay")}</th><th></th></tr></thead>
		<tbody>${rows}</tbody></table></div></div>`;
}
