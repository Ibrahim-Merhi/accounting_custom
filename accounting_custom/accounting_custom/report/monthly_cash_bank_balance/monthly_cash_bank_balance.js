frappe.query_reports["Monthly Cash Bank Balance"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "previous_from", label: __("Previous From"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_months(frappe.datetime.month_start(), -1) },
		{ fieldname: "previous_to", label: __("Previous To"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_days(frappe.datetime.month_start(), -1) },
		{ fieldname: "current_from", label: __("Current From"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_start() },
		{ fieldname: "current_to", label: __("Current To"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() }
	],
};
