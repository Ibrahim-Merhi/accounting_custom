frappe.ui.form.on("Donor", {
	setup(frm) {
		frm.set_query("account", "custom_accounts", (_doc, cdt, cdn) => {
			const row = locals[cdt][cdn];

			return {
				filters: {
					company: row.company,
					is_group: 0,
				},
			};
		});
	},
});

frappe.ui.form.on("Party Account", {
	company(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		if (row.account) {
			frappe.model.set_value(cdt, cdn, "account", null);
		}
	},
});
