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
		if (!frm.is_new() && frm.doc.docstatus===0 && !frm.doc.companies?.some(r=>r.payroll_entry)) {
			frm.add_custom_button(__("Get Employees"), () => frm.call({doc:frm.doc,method:"get_employees",freeze:true,freeze_message:__("Loading employees and salary allocations...")}).then(()=>frm.reload_doc()));
		}
		if (frm.doc.docstatus===1) {
			frm.dashboard.set_headline_alert(__("Payroll completed. Continue with each company Payroll Entry to review payment allocations and create the Bank Entry."), "green");
			frm.add_custom_button(__("Next: Company Payments"), () => show_company_payroll_entries(frm)).addClass("btn-primary");
		}
	},
	start_date(frm) {
		if (!frm.doc.start_date) return;

		frm.set_value("end_date", moment(frm.doc.start_date).endOf("month").format("YYYY-MM-DD"));
	},
	manual_deductions_add(frm) { setTimeout(()=>frm.refresh_field("manual_deductions"),0); },
});


function show_company_payroll_entries(frm) {
	const entries = (frm.doc.companies || []).filter((row) => row.payroll_entry);
	if (!entries.length) {
		frappe.msgprint(__("No company Payroll Entries were generated for this run."));
		return;
	}
	if (entries.length === 1) {
		frappe.set_route("Form", "Payroll Entry", entries[0].payroll_entry);
		return;
	}

	const escape = (value) => frappe.utils.escape_html(String(value || ""));
	const dialog = new frappe.ui.Dialog({
		title: __("Continue Payroll Processing"),
		fields: [{fieldtype: "HTML", fieldname: "payroll_entries"}],
	});
	const rows = entries.map((row) => `
		<div class="d-flex align-items-center justify-content-between border-bottom py-3">
			<div>
				<div class="font-weight-bold">${escape(row.company)}</div>
				<div class="text-muted small">${escape(row.payroll_entry)} · ${escape(row.status || __("Ready"))}</div>
			</div>
			<button class="btn btn-sm btn-primary open-company-payroll" data-payroll-entry="${escape(row.payroll_entry)}">
				${__("Open Payroll Entry")}
			</button>
		</div>`).join("");
	dialog.fields_dict.payroll_entries.$wrapper.html(`
		<p class="text-muted mb-2">${__("Complete the payment step for each company. Each entry keeps its own payable account, currency, and accounting records.")}</p>
		${rows}
	`);
	dialog.fields_dict.payroll_entries.$wrapper.on("click", ".open-company-payroll", (event) => {
		dialog.hide();
		frappe.set_route("Form", "Payroll Entry", event.currentTarget.dataset.payrollEntry);
	});
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
