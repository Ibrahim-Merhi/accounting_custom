frappe.query_reports["Employee Salary History"] = {
	filters: [
		{fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee"},
		{fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", no_default: 1},
		{fieldname: "from_date", label: __("Effective From"), fieldtype: "Date"},
		{fieldname: "to_date", label: __("Effective To"), fieldtype: "Date"},
	],
};
