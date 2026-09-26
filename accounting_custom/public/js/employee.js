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
	const roles = frappe.user_roles || [];
	const can_access = roles.includes("Accounts Manager") || frappe.session?.user === "Administrator";
	if (!can_access) {
		frm.layout.select_tab("basic_details_tab");
		frm.toggle_display("salary_information", false);
		frm.toggle_display("custom_secure_salary_section", false);
		frm.toggle_display("custom_secure_salary_profile", false);
		return;
	}
	frm.toggle_display("salary_information", true);
	frm.toggle_display("custom_secure_salary_section", true);
	frm.toggle_display("custom_secure_salary_profile", true);
	if (frm.is_new()) return;
	const field = frm.get_field("custom_secure_salary_profile");
	if (field) field.$wrapper.html(`<div class="text-muted p-3">${__("Loading salary information...")}</div>`);
	frappe.call({
		method: "accounting_custom.accounting.salary_profile.get_salary_profile_summary",
		args: {employee: frm.doc.name},
		callback: ({message}) => render_salary_workspace(frm, message || {exists: false}),
		error: () => {
			if (field) field.$wrapper.html(`<div class="text-danger p-3">${__("Unable to load salary information. Please refresh or contact the administrator.")}</div>`);
		},
	});
}

function render_salary_workspace(frm, profile) {
	const field = frm.get_field("custom_secure_salary_profile");
	if (!field) return;
	const action_label = profile.exists ? __("Edit Present Salary") : __("Create Salary Profile");
	field.$wrapper.html(`<div class="frappe-card salary-workspace">
		<div class="salary-tabs border-bottom px-3 pt-2">
			<button class="btn btn-link active" data-salary-tab="present">${__("Present Salary")}</button>
			<button class="btn btn-link" data-salary-tab="past">${__("Past Salary and Changes")} <span class="badge badge-light">${profile.revision_count || 0}</span></button>
		</div>
		<div class="salary-tab-content p-4" data-salary-panel="present">
			${render_present_salary(profile)}
			<button class="btn btn-primary btn-sm edit-salary-profile">${action_label}</button>
		</div>
		<div class="salary-tab-content p-4 hide" data-salary-panel="past">
			${render_salary_history(profile.revisions)}
			${render_salary_slips(profile.salary_slips)}
		</div>
	</div>`);
	field.$wrapper.find("[data-salary-tab]").on("click", function () {
		const tab = $(this).attr("data-salary-tab");
		field.$wrapper.find("[data-salary-tab]").removeClass("active");
		$(this).addClass("active");
		field.$wrapper.find("[data-salary-panel]").addClass("hide");
		field.$wrapper.find(`[data-salary-panel="${tab}"]`).removeClass("hide");
	});
	field.$wrapper.find(".edit-salary-profile").on("click", () => open_salary_profile_dialog(frm));
}

function render_present_salary(profile) {
	if (!profile.exists) return `<p class="text-muted">${__("No salary profile has been created for this employee.")}</p>`;
	return `<div class="row mb-3">
		${salary_total_card(__("Basic Salary"), profile.basic_salary)}
		${salary_total_card(__("Transportation"), profile.transportation)}
		${salary_total_card(__("Family Allowance"), profile.family_allowance)}
		${salary_total_card(__("Total Salary"), profile.total_salary, true)}
	</div>
	<div class="small text-muted mb-3">${__("Effective From")}: ${frappe.datetime.str_to_user(profile.effective_date)}</div>
	${render_allocation_table(__("Basic Salary"), profile.basic_allocations)}
	${render_allocation_table(__("Transportation"), profile.transportation_allocations)}
	${render_allocation_table(__("Family Allowance"), profile.family_allowance_allocations)}`;
}

function salary_total_card(label, value, emphasized = false) {
	return `<div class="col-sm-3 mb-3"><div class="border rounded p-3 h-100"><small class="text-muted">${label}</small><div class="${emphasized ? "font-weight-bold text-primary" : "font-weight-bold"}">${format_currency(value || 0)}</div></div></div>`;
}

function render_allocation_table(label, allocations) {
	if (!allocations || !allocations.length) return "";
	const rows = allocations.map((row) => `<tr><td>${escape_html(row.company)}</td><td>${escape_html(row.account)}</td><td>${escape_html(row.cost_center)}</td><td class="text-right">${format_currency(row.amount)}</td><td class="text-right">${format_percent(row.percentage)}</td></tr>`).join("");
	const total_amount = allocations.reduce((sum, row) => sum + flt(row.amount), 0);
	const total_percentage = allocations.reduce((sum, row) => sum + flt(row.percentage), 0);
	return `<div class="mb-4"><div class="d-flex justify-content-between align-items-center mb-2"><h6 class="mb-0">${label}</h6><span class="text-muted small">${allocations.length} ${__("allocation(s)")}</span></div><div class="table-responsive"><table class="table table-bordered table-hover"><thead class="bg-light"><tr><th>${__("Company")}</th><th>${__("Account")}</th><th>${__("Cost Center")}</th><th class="text-right">${__("Amount")}</th><th class="text-right">${__("Percentage")}</th></tr></thead><tbody>${rows}</tbody><tfoot><tr class="font-weight-bold"><td colspan="3">${__("Total")}</td><td class="text-right">${format_currency(total_amount)}</td><td class="text-right">${format_percent(total_percentage)}</td></tr></tfoot></table></div></div>`;
}

function render_salary_history(revisions) {
	if (!revisions || !revisions.length) return `<p class="text-muted">${__("No salary revisions yet.")}</p>`;
	const rows = revisions.map((row) => `<tr><td>${row.revision_number}</td><td>${frappe.datetime.str_to_user(row.effective_from)}</td><td>${row.effective_to ? frappe.datetime.str_to_user(row.effective_to) : __("Current")}</td><td>${frappe.datetime.str_to_user(row.action_date)}</td><td>${format_currency(row.total_salary)}</td><td>${escape_html(row.change_summary || "")}</td></tr>`).join("");
	return `<h5>${__("Salary Revision History")}</h5><div class="table-responsive"><table class="table table-bordered table-sm"><thead><tr><th>${__("Revision")}</th><th>${__("Effective From")}</th><th>${__("Effective To")}</th><th>${__("Action Date")}</th><th>${__("Total")}</th><th>${__("Changes")}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function open_salary_profile_dialog(frm) {
	frappe.call({
		method: "accounting_custom.accounting.salary_profile.get_salary_profile_editor",
		args: {employee: frm.doc.name},
		callback: ({message}) => build_salary_profile_dialog(frm, message || {exists: false}),
	});
}

function build_salary_profile_dialog(frm, data) {
	let dialog;
	const allocation_fields = () => [
		{fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", in_list_view: 1, columns: 2, reqd: 1},
		{fieldname: "account", label: __("Account"), fieldtype: "Link", options: "Account", in_list_view: 1, columns: 2, reqd: 1},
		{fieldname: "cost_center", label: __("Cost Center"), fieldtype: "Link", options: "Cost Center", in_list_view: 1, columns: 2, reqd: 1},
		{fieldname: "amount", label: __("Amount"), fieldtype: "Currency", in_list_view: 1, columns: 2, reqd: 1, non_negative: 1, onchange: () => update_salary_dialog_totals(dialog)},
		{fieldname: "percentage", label: __("Percentage"), fieldtype: "Percent", precision: "0", in_list_view: 1, columns: 2, reqd: 1, onchange: () => update_salary_dialog_totals(dialog)},
	];
	const table = (fieldname, label) => ({fieldname, label, fieldtype: "Table", cannot_add_rows: false, in_place_edit: true, data: data[fieldname] || [], fields: allocation_fields()});
	dialog = new frappe.ui.Dialog({
		title: data.exists ? __("Edit Present Salary") : __("Create Salary Profile"),
		size: "extra-large",
		fields: [
			{fieldname: "effective_date", label: __("Start Effective Date"), fieldtype: "Date", reqd: 1, default: data.effective_date || frappe.datetime.get_today()},
			{fieldname: "action_date", label: __("Date of Action"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today()},
			{fieldname: "totals_section", fieldtype: "Section Break", label: __("Salary Totals")},
			{fieldname: "basic_total", label: __("Basic Salary"), fieldtype: "Currency", read_only: 1},
			{fieldname: "transportation_total", label: __("Transportation"), fieldtype: "Currency", read_only: 1},
			{fieldname: "family_allowance_total", label: __("Family Allowance"), fieldtype: "Currency", read_only: 1},
			{fieldname: "total_salary", label: __("Total Salary"), fieldtype: "Currency", read_only: 1},
			{fieldname: "basic_section", fieldtype: "Section Break", label: __("Basic Salary Allocation")},
			table("basic_allocations", __("Basic Salary")),
			{fieldname: "basic_percentage_status", fieldtype: "HTML"},
			{fieldname: "transportation_section", fieldtype: "Section Break", label: __("Transportation Allocation")},
			table("transportation_allocations", __("Transportation")),
			{fieldname: "transportation_percentage_status", fieldtype: "HTML"},
			{fieldname: "family_section", fieldtype: "Section Break", label: __("Family Allowance Allocation")},
			table("family_allowance_allocations", __("Family Allowance")),
			{fieldname: "family_allowance_percentage_status", fieldtype: "HTML"},
		],
		primary_action_label: __("Save Salary Profile"),
		primary_action(values) {
			update_salary_dialog_totals(dialog);
			const payload = {employee: frm.doc.name, effective_date: values.effective_date, action_date: values.action_date};
			for (const fieldname of salary_table_fields()) payload[fieldname] = dialog.get_value(fieldname) || [];
			dialog.disable_primary_action();
			frappe.call({
				method: "accounting_custom.accounting.salary_profile.save_salary_profile_from_employee",
				args: {payload: JSON.stringify(payload)},
				callback: () => { dialog.hide(); render_secure_salary_profile(frm); },
				always: () => dialog.enable_primary_action(),
			});
		},
	});
	for (const fieldname of salary_table_fields()) {
		const grid = dialog.fields_dict[fieldname].grid;
		grid.get_field("account").get_query = (doc) => ({filters: doc.company ? {company: doc.company, is_group: 0, disabled: 0} : {name: ["=", ""]}});
		grid.get_field("cost_center").get_query = (doc) => ({filters: doc.company ? {company: doc.company, is_group: 0, disabled: 0} : {name: ["=", ""]}});
	}
	dialog.$wrapper.on("change click", ".grid-row input, .grid-add-row, .grid-remove-rows, .grid-delete-row", () => setTimeout(() => update_salary_dialog_totals(dialog), 0));
	dialog.show();
	update_salary_dialog_totals(dialog);
}

function salary_table_fields() {
	return ["basic_allocations", "transportation_allocations", "family_allowance_allocations"];
}

function update_salary_dialog_totals(dialog) {
	if (!dialog) return;
	const totals = {};
	for (const fieldname of salary_table_fields()) {
		const rows = dialog.get_value(fieldname) || [];
		const total = flt(rows.reduce((sum, row) => sum + flt(row.amount), 0), 2);
		const percentage_total = flt(rows.reduce((sum, row) => sum + flt(row.percentage), 0), 6);
		totals[fieldname] = total;
		dialog.fields_dict[fieldname].grid.refresh();
		const status_field = `${fieldname.replace("_allocations", "")}_percentage_status`;
		const is_valid = Math.abs(percentage_total - 100) <= 0.001;
		const status_class = is_valid ? "text-success" : "text-danger";
		const status_text = rows.length ? `${__("Percentage Total")}: ${format_percent(percentage_total)}` : __("No allocation rows");
		if (dialog.fields_dict[status_field]) {
			dialog.fields_dict[status_field].$wrapper.html(`<div class="${status_class} font-weight-bold text-right mb-2">${status_text}</div>`);
		}
	}
	dialog.set_value("basic_total", totals.basic_allocations || 0);
	dialog.set_value("transportation_total", totals.transportation_allocations || 0);
	dialog.set_value("family_allowance_total", totals.family_allowance_allocations || 0);
	dialog.set_value("total_salary", flt(totals.basic_allocations) + flt(totals.transportation_allocations) + flt(totals.family_allowance_allocations));
}

function render_salary_slips(slips) {
	if (!slips || !slips.length) return "";
	const rows = slips.map((slip) => `<tr><td><a href="/app/salary-slip/${encodeURIComponent(slip.name)}">${escape_html(slip.name)}</a></td><td>${escape_html(slip.company)}</td><td>${frappe.datetime.str_to_user(slip.start_date)} – ${frappe.datetime.str_to_user(slip.end_date)}</td><td>${format_currency(slip.net_pay, slip.currency)}</td><td><a class="btn btn-xs btn-default" target="_blank" href="/printview?doctype=Salary%20Slip&name=${encodeURIComponent(slip.name)}&trigger_print=1">${__("Print")}</a></td></tr>`).join("");
	return `<div class="mt-4"><h5>${__("Salary Slips")}</h5><div class="table-responsive"><table class="table table-bordered table-sm"><thead><tr><th>${__("Salary Slip")}</th><th>${__("Company")}</th><th>${__("Period")}</th><th>${__("Net Pay")}</th><th></th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
}

function format_percent(value) {
	return `${flt(value, 0)}%`;
}

function escape_html(value) {
	return frappe.utils.escape_html(value || "");
}
