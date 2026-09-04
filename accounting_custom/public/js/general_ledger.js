(() => {
	const reportName = "General Ledger";
	const fieldname = "add_values_in_transaction_currency";
	let retryTimer;

	function isGeneralLedgerRoute() {
		const route = frappe.get_route();
		return route[0] === "query-report" && route[1] === reportName;
	}

	function enableTransactionCurrencyColumns(attempt = 0) {
		if (!isGeneralLedgerRoute()) return;

		const definition = frappe.query_reports?.[reportName];
		const filterDefinition = definition?.filters?.find(
			(filter) => filter.fieldname === fieldname
		);
		if (filterDefinition) filterDefinition.default = 1;

		const report = frappe.query_report;
		const filter = report?.get_filter?.(fieldname);
		if (!filter) {
			if (attempt < 20) {
				clearTimeout(retryTimer);
				retryTimer = setTimeout(
					() => enableTransactionCurrencyColumns(attempt + 1),
					100
				);
			}
			return;
		}

		filter.df.default = 1;
		if (!filter.get_value()) {
			report.set_filter_value(fieldname, 1);
		}
	}

	frappe.router.on("change", () => enableTransactionCurrencyColumns());
	frappe.after_ajax(() => enableTransactionCurrencyColumns());
})();
