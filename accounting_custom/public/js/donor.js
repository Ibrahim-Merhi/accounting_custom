frappe.ui.form.on("Donor", {
	setup(frm) {
		set_donor_account_queries(frm);
	},

	refresh(frm) {
		set_donor_account_queries(frm);
	},
});

frappe.ui.form.on("Party Account", {
	company(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "account", null);
		frappe.model.set_value(cdt, cdn, "advance_account", null);
	},
});

function set_donor_account_queries(frm) {
	["account", "advance_account"].forEach((fieldname) => {
		frm.set_query(fieldname, "custom_accounts", (_doc, cdt, cdn) => {
			const row = locals[cdt][cdn];

			return {
				query: "erpnext.controllers.queries.get_account_list",
				filters: row.company
					? { company: row.company, disabled: 0, is_group: 0 }
					: { name: ["=", ""] },
			};
		});
	});
}
