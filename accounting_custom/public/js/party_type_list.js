frappe.listview_settings["Party Type"] = {
	onload(listview) {
		const allowed_roles = [
			"System Manager",
			"Accounts Manager",
			"Accounts User",
			"Finance Officer",
			"Treasurer",
		];
		if (!(frappe.user_roles || []).some((role) => allowed_roles.includes(role))) return;

		listview.can_create = true;
		listview.page.set_primary_action(
			__("Add Party Type"),
			() => frappe.new_doc("Party Type"),
			"add"
		);
	},
};
