frappe.ui.form.on("Collector Profile", {
	setup(frm) {
		frm.set_query("default_donor_account", () => ({
			filters: frm.doc.company
				? { company: frm.doc.company, is_group: 0, disabled: 0 }
				: { name: ["=", ""] },
		}));
		frm.set_query("account", "custody_accounts", () => ({
			filters: frm.doc.company
				? { company: frm.doc.company, is_group: 0, disabled: 0 }
				: { name: ["=", ""] },
		}));
	},
});
