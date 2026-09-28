frappe.ui.form.on("Multi Company Payroll Run", {
	setup(frm) {
		frm.set_query("payroll_payable_account", "companies", (_doc, cdt, cdn) => ({filters:{company:locals[cdt][cdn].company,is_group:0,disabled:0,account_type:"Payable"}}));
		frm.set_query("employee", "manual_deductions", () => ({filters:{name:["in",(frm.doc.employees||[]).map(r=>r.employee)]}}));
		frm.set_query("company", "manual_deductions", (_doc, cdt, cdn) => {
			const employee = locals[cdt][cdn].employee;
			const companies = get_employee_companies(frm, employee);
			return {filters:{name:["in",companies]}};
		});
		frm.set_query("salary_component", "manual_deductions", () => ({filters:{type:"Deduction",disabled:0}}));
		frm.set_query("source_account", "manual_deductions", (_doc, cdt, cdn) => ({filters:{name:["in",get_source_allocations(frm, locals[cdt][cdn]).map(r=>r.account)]}}));
		frm.set_query("source_cost_center", "manual_deductions", (_doc, cdt, cdn) => ({filters:{name:["in",get_source_allocations(frm, locals[cdt][cdn]).filter(r=>!locals[cdt][cdn].source_account || r.account===locals[cdt][cdn].source_account).map(r=>r.cost_center)]}}));
	},
	refresh(frm) {
		render_company_summary(frm);
		if (!frm.is_new() && frm.doc.docstatus===0 && !frm.doc.companies?.some(r=>r.payroll_entry)) {
			frm.add_custom_button(__("Get Employees"), () => frm.call({doc:frm.doc,method:"get_employees",freeze:true,freeze_message:__("Loading employees and salary allocations...")}).then(()=>frm.reload_doc()));
		}
		if (frm.doc.docstatus===1) {
			frm.add_custom_button(__("4 per A4"), () => print_payslips(frm, "Payroll Payslips - 4 per A4"), __("Print Payslips"));
			frm.add_custom_button(__("6 per A4"), () => print_payslips(frm, "Payroll Payslips - 6 per A4"), __("Print Payslips"));
			frm.dashboard.set_headline_alert(__("Payroll completed. Continue with each company Payroll Entry to review payment allocations and create the Bank Entry."), "green");
			frm.add_custom_button(__("Company Payments"), () => show_company_payroll_entries(frm)).addClass("btn-primary");
		}
	},
	onload(frm) {
		if (frm.is_new()) {
			frm.set_value("payroll_month", moment().format("MMMM"));
			frm.set_value("payroll_year", moment().year());
		}
	},
	manual_deductions_add(frm) { setTimeout(()=>frm.refresh_field("manual_deductions"),0); },
});


function payroll_entries(frm) {
	const entries = new Map();
	(frm.doc.employees || []).forEach((row) => {
		if (row.source_payroll_entry) entries.set(row.source_payroll_entry, {payroll_entry: row.source_payroll_entry, company: row.company, status: row.status});
	});
	(frm.doc.companies || []).forEach((row) => {
		if (row.payroll_entry) entries.set(row.payroll_entry, {payroll_entry: row.payroll_entry, company: row.company, status: row.status});
	});
	return [...entries.values()];
}

function render_company_summary(frm) {
	const submitted = frm.doc.docstatus === 1;
	frm.toggle_display("company_summary_html", submitted);
	frm.toggle_display("companies", !submitted);
	if (!submitted || !frm.fields_dict.company_summary_html) return;
	const escape = (value) => frappe.utils.escape_html(String(value || ""));
	const summaries = new Map();
	(frm.doc.companies || []).forEach((row) => {
		if (!summaries.has(row.company)) summaries.set(row.company, {company: row.company, account: row.payroll_payable_account, currency: row.currency, gross: 0, employees: new Set(), entries: new Set()});
		const item = summaries.get(row.company); item.gross += flt(row.gross_salary); if (row.payroll_entry) item.entries.add(row.payroll_entry);
	});
	(frm.doc.employees || []).forEach((row) => {
		if (!summaries.has(row.company)) summaries.set(row.company, {company: row.company, account: "", currency: "", gross: 0, employees: new Set(), entries: new Set()});
		const item = summaries.get(row.company); item.employees.add(row.employee); if (row.source_payroll_entry) item.entries.add(row.source_payroll_entry);
	});
	const rows = [...summaries.values()].map((item) => `<tr><td><strong>${escape(item.company)}</strong></td><td>${escape(item.account)}</td><td>${escape(item.currency)}</td><td class="text-right">${item.employees.size}</td><td class="text-right">${format_currency(item.gross, item.currency, 0)}</td><td>${[...item.entries].map(name => `<a href="/app/payroll-entry/${encodeURIComponent(name)}">${escape(name)}</a>`).join("<br>")}</td><td><span class="indicator-pill green">${__("Completed")}</span></td></tr>`).join("");
	frm.fields_dict.company_summary_html.$wrapper.html(`<div class="table-responsive"><table class="table table-bordered"><thead class="bg-light"><tr><th>${__("Company")}</th><th>${__("Payroll Payable Account")}</th><th>${__("Currency")}</th><th class="text-right">${__("Employees")}</th><th class="text-right">${__("Gross Salary")}</th><th>${__("Payroll Entries")}</th><th>${__("Status")}</th></tr></thead><tbody>${rows}</tbody></table></div>`);
}

function show_company_payroll_entries(frm) {
	const entries = payroll_entries(frm);
	if (!entries.length) { frappe.msgprint(__("No company Payroll Entries were generated for this run.")); return; }
	if (entries.length === 1) { frappe.set_route("Form", "Payroll Entry", entries[0].payroll_entry); return; }
	const escape = (value) => frappe.utils.escape_html(String(value || ""));
	const dialog = new frappe.ui.Dialog({title: __("Continue Payroll Processing"), fields: [{fieldtype: "HTML", fieldname: "payroll_entries"}]});
	const rows = entries.map((row) => `<div class="d-flex align-items-center justify-content-between border-bottom py-3"><div><div class="font-weight-bold">${escape(row.company)}</div><div class="text-muted small">${escape(row.payroll_entry)} · ${escape(row.status || __("Ready"))}</div></div><button class="btn btn-sm btn-primary open-company-payroll" data-payroll-entry="${escape(row.payroll_entry)}">${__("Open Payroll Entry")}</button></div>`).join("");
	dialog.fields_dict.payroll_entries.$wrapper.html(`<p class="text-muted mb-2">${__("Complete the payment step for each underlying Payroll Entry. The summary remains one row per company.")}</p>${rows}`);
	dialog.fields_dict.payroll_entries.$wrapper.on("click", ".open-company-payroll", (event) => {dialog.hide(); frappe.set_route("Form", "Payroll Entry", event.currentTarget.dataset.payrollEntry);});
	dialog.show();
}

frappe.ui.form.on("Multi Company Payroll Deduction", {
	employee(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const companies = get_employee_companies(frm, row.employee);
		const company = companies.length === 1 ? companies[0] : "";

		frappe.model.set_value(cdt, cdn, "company", company).then(() => {
			map_deduction_employee(frm, cdt, cdn);
		});
	},
	company(frm, cdt, cdn) { map_deduction_employee(frm, cdt, cdn); clear_source(frm, cdt, cdn); },
	source_component(frm, cdt, cdn) { clear_source(frm, cdt, cdn); autofill_source(frm, cdt, cdn); },
	source_account(frm, cdt, cdn) { frappe.model.set_value(cdt, cdn, "source_cost_center", ""); autofill_source(frm, cdt, cdn); },
});

function get_source_allocations(frm, row) {
	return (frm.doc.allocation_summary || []).filter((allocation) =>
		allocation.employee === row.employee && allocation.company === row.company && allocation.component === row.source_component
	);
}

function clear_source(_frm, cdt, cdn) {
	frappe.model.set_value(cdt, cdn, "source_account", "");
	frappe.model.set_value(cdt, cdn, "source_cost_center", "");
}

function autofill_source(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const allocations = get_source_allocations(frm, row);
	const accounts = [...new Set(allocations.map(r=>r.account))];
	if (!row.source_account && accounts.length === 1) frappe.model.set_value(cdt, cdn, "source_account", accounts[0]);
	const cost_centers = [...new Set(allocations.filter(r=>!row.source_account || r.account===row.source_account).map(r=>r.cost_center))];
	if (cost_centers.length === 1) frappe.model.set_value(cdt, cdn, "source_cost_center", cost_centers[0]);
}

function get_employee_companies(frm, employee) {
	if (!employee) return [];

	return [...new Set(
		(frm.doc.employees || [])
			.filter((row) => row.employee === employee && row.company)
			.map((row) => row.company)
	)];
}

function map_deduction_employee(frm, cdt, cdn) {
	const row=locals[cdt][cdn];
	const match=(frm.doc.employees||[]).find(e=>e.employee===row.employee && e.company===row.company);
	frappe.model.set_value(cdt,cdn,"payroll_employee",match?.payroll_employee||"");
}

frappe.ui.form.on("Multi Company Payroll Employee", {
	pay_this_run(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const available = flt(row.net_salary) - flt(row.previously_paid);
		if (flt(row.pay_this_run) < 0) frappe.model.set_value(cdt, cdn, "pay_this_run", 0);
		if (flt(row.pay_this_run) > available) frappe.model.set_value(cdt, cdn, "pay_this_run", available);
		frappe.model.set_value(cdt, cdn, "deferred_amount", Math.max(available - flt(row.pay_this_run), 0));
	},
});

function print_payslips(frm, format) {
	const url = `/printview?doctype=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.docname)}&format=${encodeURIComponent(format)}&no_letterhead=1&trigger_print=1`;
	window.open(url, "_blank");
}
