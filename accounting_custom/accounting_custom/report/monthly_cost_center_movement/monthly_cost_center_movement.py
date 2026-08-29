from accounting_custom.reporting.management_reports import monthly_cost_center_movement


def execute(filters=None):
	return monthly_cost_center_movement(filters or {})
