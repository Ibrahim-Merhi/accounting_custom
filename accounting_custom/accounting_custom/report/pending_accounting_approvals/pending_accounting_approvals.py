from accounting_custom.reporting.management_reports import pending_approvals


def execute(filters=None):
	return pending_approvals(filters or {})
