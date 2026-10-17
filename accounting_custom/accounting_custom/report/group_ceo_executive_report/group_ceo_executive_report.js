frappe.query_reports["Group CEO Executive Report"] = {
	filters: [
		{
			fieldname: "category", label: __("Report"), fieldtype: "Select", reqd: 1,
			options: ["Active Employees", "Pending Leaves", "Clocked In Today", "No Clock-in Today", "Payroll YTD", "Donors", "Beneficiaries", "Orphans", "Families", "Relief Orders", "Relief Statements", "Beneficiary Activities", "Donations YTD"].join("\n"),
			default: "Active Employees",
		},
		{fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company"},
		{fieldname: "date", label: __("Date"), fieldtype: "Date", default: frappe.datetime.get_today()},
		{fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: `${frappe.datetime.get_today().slice(0, 4)}-01-01`},
		{fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today()},
	],
};
