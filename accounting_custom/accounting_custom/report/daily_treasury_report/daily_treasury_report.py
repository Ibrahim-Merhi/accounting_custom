from accounting_custom.reporting.management_reports import daily_treasury


def execute(filters=None):
	return daily_treasury(filters or {})
