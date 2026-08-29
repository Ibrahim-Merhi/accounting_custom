from accounting_custom.reporting.management_reports import collector_collections


def execute(filters=None):
	return collector_collections(filters or {})
