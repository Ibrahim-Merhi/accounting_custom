frappe.listview_settings["Employee"] = {
	onload(listview) {
		const has_identity_filter = listview.filter_area.get().some((filter) => filter[1] === "custom_is_payroll_identity");
		if (!has_identity_filter) {
			listview.filter_area.add([["Employee", "custom_is_payroll_identity", "=", 0]]);
		}
	},
};
