frappe.query_reports["Account and Cost Center Report"] = {
	filters: [
		{
			fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
			on_change() {
				frappe.query_report.set_filter_value("cost_center", "");
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "fiscal_year", label: __("Fiscal Year"), fieldtype: "Link", options: "Fiscal Year",
			on_change() {
				const fiscal_year = frappe.query_report.get_filter_value("fiscal_year");
				if (!fiscal_year) return;
				frappe.db.get_value("Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"]).then((r) => {
					frappe.query_report.set_filter_value({
						from_date: r.message?.year_start_date || "",
						to_date: r.message?.year_end_date || "",
					});
				});
			},
		},
		{fieldname: "from_date", label: __("From Date"), fieldtype: "Date"},
		{fieldname: "to_date", label: __("To Date"), fieldtype: "Date"},
		{fieldname: "from_account_number", label: __("From Account Number"), fieldtype: "Data"},
		{fieldname: "to_account_number", label: __("To Account Number"), fieldtype: "Data"},
		{
			fieldname: "cost_center", label: __("Cost Center"), fieldtype: "Link", options: "Cost Center",
			get_query() {
				const company = frappe.query_report.get_filter_value("company");
				return company ? {filters: {company}} : {};
			},
		},
		{
			fieldname: "with_period_closing_entry_for_opening",
			label: __("With Period Closing Entry For Opening Balances"), fieldtype: "Check", default: 1,
		},
		{
			fieldname: "with_period_closing_entry_for_current_period",
			label: __("Period Closing Entry For Current Period"), fieldtype: "Check", default: 1,
		},
		{fieldname: "show_zero_values", label: __("Show Zero Values"), fieldtype: "Check", default: 0},
	],
	tree: true,
	name_field: "row_id",
	parent_field: "parent_row_id",
	initial_depth: 1,
	onload: prepare_wide_account_report,
	after_refresh: prepare_wide_account_report,
	formatter(value, row, column, data, default_formatter) {
		let formatted = default_formatter(value, row, column, data);
		if (data?.is_account_row) formatted = `<strong>${formatted}</strong>`;
		return formatted;
	},
};

function prepare_wide_account_report(report) {
	if (!report?.page?.wrapper) return;
	$(report.page.wrapper).addClass("account-cost-center-wide-report");
	if (document.getElementById("account-cost-center-wide-report-style")) return;
	const style = document.createElement("style");
	style.id = "account-cost-center-wide-report-style";
	style.textContent = `
		.account-cost-center-wide-report .report-wrapper { overflow-x: auto !important; }
		.account-cost-center-wide-report .datatable { min-width: 1220px !important; }
		.account-cost-center-wide-report .datatable .dt-scrollable,
		.account-cost-center-wide-report .datatable .dt-scrollable__body {
			overflow-x: auto !important;
		}
	`;
	document.head.appendChild(style);
}
