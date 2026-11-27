const arabicNameFields = {
	Account: ["account_name", "custom_account_name_arabic"],
	Company: ["company_name", "custom_company_name_arabic"],
	"Cost Center": ["cost_center_name", "custom_cost_center_name_arabic"],
};

frappe.ui.form.on("Company", {
	setup(frm) {
		frm.set_query("custom_default_payroll_payment_account", () => ({ filters: {
			company: frm.doc.name, is_group: 0, disabled: 0,
			account_type: ["in", ["Bank", "Cash"]],
		} }));
	},
});

frappe.ui.form.on("Cost Center", {
	refresh(frm) {
		const is_root = Boolean(frm.doc.company && frm.doc.cost_center_name === frm.doc.company);
		frm.set_df_property("parent_cost_center", "mandatory_depends_on", "");
		frm.toggle_reqd("parent_cost_center", false);
		frm.toggle_display(["parent_cost_center", "custom_parent_cost_center_arabic"], !is_root);
		const field = "custom_company_name_arabic";
		frm.set_df_property(field, "fetch_from", "");
		frm.set_df_property(field, "read_only_depends_on", "");
		frm.toggle_enable(field, true);
	},
});

for (const [doctype, [sourceField, arabicField]] of Object.entries(arabicNameFields)) {
	frappe.ui.form.on(doctype, {
		[sourceField](frm) {
			const source = frm.doc[sourceField];
			if (!source || frm.doc.custom_arabic_name_source === source) return;
			frappe.call({
				method: "accounting_custom.accounting.cost_center.get_arabic_translation",
				args: { source_text: source },
				freeze: false,
				callback: ({ message }) => {
					if (!message) return;
					frm.set_value(arabicField, message);
					frm.set_value("custom_arabic_name_source", source);
				},
			});
		},
	});
}
