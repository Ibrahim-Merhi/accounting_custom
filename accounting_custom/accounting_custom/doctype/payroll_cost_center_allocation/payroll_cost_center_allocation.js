frappe.ui.form.on("Payroll Cost Center Allocation", {
	setup(frm) {
		frm.set_query("salary_structure_assignment", () => ({
			filters: frm.doc.employee
				? { employee: frm.doc.employee, company: frm.doc.company, docstatus: 1 }
				: { name: ["=", ""] },
		}));
		frm.set_query("cost_center", "allocations", () => ({
			filters: frm.doc.company ? { company: frm.doc.company, is_group: 0 } : { name: ["=", ""] },
		}));
	},
	employee(frm) {
		frm.set_value("salary_structure_assignment", null);
		frm.clear_table("allocations");
		frm.refresh_field("allocations");
	},
});
