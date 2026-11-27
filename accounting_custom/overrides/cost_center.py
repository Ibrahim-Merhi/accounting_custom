from erpnext.accounts.doctype.cost_center.cost_center import CostCenter


class CustomCostCenter(CostCenter):
	def _get_missing_mandatory_fields(self):
		missing = super()._get_missing_mandatory_fields()
		# ERPNext's controller permits a blank parent on the company root.
		# Honor that rule even if the site's field metadata marks it required.
		if self.company and self.cost_center_name == self.company:
			return [(field, message) for field, message in missing if field != "parent_cost_center"]
		return missing
