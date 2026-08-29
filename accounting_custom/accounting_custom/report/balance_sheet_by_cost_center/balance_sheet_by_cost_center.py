from accounting_custom.reporting.management_reports import balance_sheet_by_cost_center


def execute(filters=None):
	return balance_sheet_by_cost_center(filters or {})
