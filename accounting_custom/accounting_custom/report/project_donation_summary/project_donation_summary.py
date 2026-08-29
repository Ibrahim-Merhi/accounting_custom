from accounting_custom.reporting.management_reports import project_donations


def execute(filters=None):
	return project_donations(filters or {})
