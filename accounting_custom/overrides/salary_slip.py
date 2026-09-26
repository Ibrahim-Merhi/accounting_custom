from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip


class CustomSalarySlip(SalarySlip):
	def add_tax_components(self):
		"""Managed salary profiles intentionally contain no automatic tax deductions."""
		if (self.salary_structure or "").startswith("Managed-"):
			self.other_deduction_components = [
				row.salary_component for row in self.get("deductions")
			]
			self._component_based_variable_tax = {}
			return
		return super().add_tax_components()
