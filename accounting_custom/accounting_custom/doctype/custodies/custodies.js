frappe.ui.form.on("Custodies", {
	setup(frm) {
		frm.set_query("account", () => ({
			filters: frm.doc.company
				? { company: frm.doc.company, account_type: "Receivable", is_group: 0, disabled: 0 }
				: { name: ["=", ""] },
		}));
	},
	company(frm) {
		frm.set_value("account", null);
	},
});
