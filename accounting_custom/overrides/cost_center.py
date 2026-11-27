from erpnext.accounts.doctype.cost_center.cost_center import CostCenter


class CustomCostCenter(CostCenter):
	def validate_mandatory(self):
		if self.parent_cost_center:
			super().validate_mandatory()

	def _get_missing_mandatory_fields(self):
		missing = super()._get_missing_mandatory_fields()
		return [(field, message) for field, message in missing if field != "parent_cost_center"]
