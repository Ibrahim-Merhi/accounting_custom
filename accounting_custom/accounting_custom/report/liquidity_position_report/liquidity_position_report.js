frappe.query_reports["Liquidity Position Report"] = {
	filters: [
		{
			fieldname: "companies",
			label: __("Companies"),
			fieldtype: "MultiSelectList",
			get_data: (txt) => frappe.db.get_link_options("Company", txt),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "report_page",
			label: __("Report Page"),
			fieldtype: "Select",
			options: [
				{ value: "liquidity", label: __("Liquidity Report") },
				{ value: "movement", label: __("Liquidity Movement") },
				{ value: "summary", label: __("Group Summary") },
			],
			default: "liquidity",
			reqd: 1,
		},
		{
			fieldname: "groups_only",
			label: __("Groups Only"),
			fieldtype: "Check",
			default: 0,
		},
	],
	tree: true,
	name_field: "cost_center",
	parent_field: "parent_cost_center",
	initial_depth: 1,
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (data.is_group) value = `<strong>${value}</strong>`;
		if (["available_liquidity", "ending_liquidity", "balance_liquidity"].includes(column.fieldname)) {
			value = `<span style="color:${flt(data[column.fieldname]) < 0 ? "#c62828" : "#16825d"};font-weight:600">${value}</span>`;
		}
		if (["check", "difference"].includes(column.fieldname) && Math.abs(flt(data[column.fieldname])) >= 2) {
			value = `<span style="color:#c62828;font-weight:700">${value}</span>`;
		}
		return value;
	},
	onload(report) {
		report.page.add_inner_button(__("Configure Accounts"), () => {
			frappe.set_route("List", "Account", { custom_liquidity_report_classification: ["is", "not set"] });
		});
	},
};
