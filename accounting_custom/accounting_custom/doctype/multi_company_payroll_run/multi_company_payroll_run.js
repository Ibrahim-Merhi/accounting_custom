frappe.ui.form.on("Multi Company Payroll Run", {
	setup(frm) {
		frm.set_query("payroll_payable_account", "companies", (_doc, cdt, cdn) => ({filters:{company:locals[cdt][cdn].company,is_group:0,disabled:0,account_type:""}}));
		frm.set_query("employee", "manual_deductions", () => ({filters:{name:["in",(frm.doc.employees||[]).map(r=>r.employee)]}}));
		frm.set_query("company", "manual_deductions", () => ({filters:{name:["in",(frm.doc.companies||[]).map(r=>r.company)]}}));
		frm.set_query("salary_component", "manual_deductions", () => ({filters:{type:"Deduction",disabled:0}}));
	},
	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus===0 && !frm.doc.companies?.some(r=>r.payroll_entry)) {
			frm.add_custom_button(__("Get Employees"), () => frm.call({doc:frm.doc,method:"get_employees",freeze:true,freeze_message:__("Loading employees and salary allocations...")}).then(()=>frm.reload_doc()));
		}
		if (frm.doc.docstatus===1) frm.dashboard.set_headline_alert(__("Payroll completed. Open company Payroll Entries, Salary Slips, and Journal Entries from the tables below."), "green");
	},
	manual_deductions_add(frm) { setTimeout(()=>frm.refresh_field("manual_deductions"),0); },
});

frappe.ui.form.on("Multi Company Payroll Deduction", {
	employee(frm, cdt, cdn) { map_deduction_employee(frm, cdt, cdn); },
	company(frm, cdt, cdn) { map_deduction_employee(frm, cdt, cdn); },
});

function map_deduction_employee(frm, cdt, cdn) {
	const row=locals[cdt][cdn];
	const match=(frm.doc.employees||[]).find(e=>e.employee===row.employee && e.company===row.company);
	frappe.model.set_value(cdt,cdn,"payroll_employee",match?.payroll_employee||"");
}
