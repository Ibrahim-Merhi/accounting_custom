frappe.query_reports["Group CEO Executive Report"] = {
	onload(report) {
		set_filter_visibility(report);
	},
	filters: [
		{
			fieldname: "category", label: __("Choose a Report"), fieldtype: "Select", reqd: 1,
			options: ["Active Employees", "My Pending Leave Approvals", "Pending Leaves", "Clocked In Today", "No Clock-in Today", "Payroll Since January 1", "Donors", "Beneficiaries", "Orphans", "Families", "Relief Orders", "Relief Statements", "Beneficiary Activities", "Donations Since January 1"].join("\n"),
			default: "Active Employees",
			on_change(report) {
				set_filter_visibility(report);
				report.refresh();
			},
		},
		{fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company"},
		{fieldname: "date", label: __("Date"), fieldtype: "Date", default: frappe.datetime.get_today()},
		{fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: `${frappe.datetime.get_today().slice(0, 4)}-01-01`},
		{fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today()},
	],
};

function set_filter_visibility(report) {
	const category = report.get_filter_value("category");
	const single_date = ["Active Employees", "Clocked In Today", "No Clock-in Today"].includes(category);
	const date_range = ["Payroll Since January 1", "Donations Since January 1"].includes(category);
	report.get_filter("date").toggle(single_date);
	report.get_filter("from_date").toggle(date_range);
	report.get_filter("to_date").toggle(date_range);
}
