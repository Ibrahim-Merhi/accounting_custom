from accounting_custom.reporting.management_reports import donor_history


def execute(filters=None):
	return donor_history(filters or {})
