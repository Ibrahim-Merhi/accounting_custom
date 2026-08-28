frappe.ui.form.on("Journal Entry", {
	setup(frm) {
		frm.set_query("custom_branch", () => ({
			filters: frm.doc.company ? { custom_company: frm.doc.company } : { name: ["=", ""] },
		}));
	},

	company(frm) {
		frm.set_value("custom_branch", null);
	},
});
