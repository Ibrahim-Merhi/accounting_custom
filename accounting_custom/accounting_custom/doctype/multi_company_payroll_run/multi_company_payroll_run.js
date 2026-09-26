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
	},
	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus===0 && !frm.doc.companies?.some(r=>r.payroll_entry)) {
			frm.add_custom_button(__("Get Employees"), () => frm.call({doc:frm.doc,method:"get_employees",freeze:true,freeze_message:__("Loading employees and salary allocations...")}).then(()=>frm.reload_doc()));
		}
		if (frm.doc.docstatus===1) frm.dashboard.set_headline_alert(__("Payroll completed. Open company Payroll Entries, Salary Slips, and Journal Entries from the tables below."), "green");
	},
	start_date(frm) {
		if (!frm.doc.start_date) return;

		frm.set_value("end_date", moment(frm.doc.start_date).endOf("month").format("YYYY-MM-DD"));
	},
	manual_deductions_add(frm) { setTimeout(()=>frm.refresh_field("manual_deductions"),0); },
});

frappe.ui.form.on("Multi Company Payroll Deduction", {
	employee(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const companies = get_employee_companies(frm, row.employee);
		const company = companies.length === 1 ? companies[0] : "";

		frappe.model.set_value(cdt, cdn, "company", company).then(() => {
			map_deduction_employee(frm, cdt, cdn);
		});
	},
	company(frm, cdt, cdn) { map_deduction_employee(frm, cdt, cdn); },
});

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
