frappe.ui.form.on("Journal Entry", {
	setup(frm) {
		frm.set_query("custom_branch", "accounts", () => ({
			filters: frm.doc.company ? { custom_company: frm.doc.company } : { name: ["=", ""] },
		}));
	},

	company(frm) {
		(frm.doc.accounts || []).forEach((row) => {
			frappe.model.set_value(row.doctype, row.name, "custom_branch", null);
		});
	},
});
