from accounting_custom.reporting.management_reports import period_balance_comparison


def execute(filters=None):
	return period_balance_comparison(filters or {})
