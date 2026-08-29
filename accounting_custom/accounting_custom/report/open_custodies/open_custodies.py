from accounting_custom.reporting.management_reports import open_custodies


def execute(filters=None):
	return open_custodies(filters or {})
