import frappe

from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip


class CustomSalarySlip(SalarySlip):
	def check_sal_struct(self):
		"""Select the assignment valid on the employee's actual payroll start."""
		cutoff = self.actual_start_date or self.start_date
		frequency_condition = ""
		params = {"employee": self.employee, "cutoff": cutoff}
		if not self.salary_slip_based_on_timesheet and self.payroll_frequency:
			frequency_condition = "and ss.payroll_frequency=%(payroll_frequency)s"
			params["payroll_frequency"] = self.payroll_frequency
		result = frappe.db.sql(f"""
			select ssa.salary_structure
			from `tabSalary Structure Assignment` ssa
			inner join `tabSalary Structure` ss on ss.name=ssa.salary_structure
			where ssa.docstatus=1 and ss.docstatus=1 and ss.is_active='Yes'
			and ssa.employee=%(employee)s and ssa.from_date<=%(cutoff)s
			{frequency_condition}
			order by ssa.from_date desc, ssa.creation desc limit 1
		""", params)
		if result:
			self.salary_structure = result[0][0]
			return self.salary_structure

	def add_tax_components(self):
		"""Managed salary profiles intentionally contain no automatic tax deductions."""
		if (self.salary_structure or "").startswith("Managed-"):
			self.other_deduction_components = [
				row.salary_component for row in self.get("deductions")
			]
			self._component_based_variable_tax = {}
			return
		return super().add_tax_components()
