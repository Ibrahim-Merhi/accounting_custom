import frappe
from frappe.tests.utils import FrappeTestCase

from accounting_custom.accounting.salary_profile import get_revision_history, get_salary_profile_summary
from accounting_custom.accounting.payroll import create_manual_deductions, cancel_manual_deductions
from accounting_custom.permissions import salary_permission, salary_query


class TestEmployeeSalarySecurity(FrappeTestCase):
	def test_component_totals_are_derived_and_only_one_component_is_required(self):
		profile = frappe.new_doc("Employee Salary Profile")
		profile.append("basic_allocations", {"amount": 300})
		profile.append("basic_allocations", {"amount": 700})
		profile._calculate_component_totals()
		self.assertEqual(profile.basic_salary, 1000)
		self.assertEqual(profile.transportation, 0)
		self.assertEqual(profile.family_allowance, 0)
		empty_profile = frappe.new_doc("Employee Salary Profile")
		with self.assertRaises(frappe.ValidationError):
			empty_profile._calculate_component_totals()

	def test_multiple_companies_create_internal_payroll_identity(self):
		frappe.set_user("Administrator")
		branch = frappe.get_doc({"doctype": "Branch", "branch": "Payroll Identity Test", "custom_company": "_Test Company"}).insert(ignore_permissions=True)
		employee = frappe.get_doc({
			"doctype": "Employee", "first_name": "Multi Company Test", "gender": "Male",
			"date_of_birth": "1990-01-01", "date_of_joining": "2026-01-01",
			"status": "Active", "company": "Itihad",
			"custom_branches": [
				{"company": "Itihad", "branch": "Tripoli", "from_date": "2026-01-01"},
				{"company": "_Test Company", "branch": branch.name, "from_date": "2026-02-01"},
			],
		}).insert(ignore_permissions=True)
		identity = frappe.db.get_value("Employee", {"custom_master_employee": employee.name, "company": "_Test Company"}, ["name", "custom_is_payroll_identity"], as_dict=True)
		self.assertTrue(identity and identity.custom_is_payroll_identity)
		primary_identity = frappe.db.get_value("Employee", {"custom_master_employee": employee.name, "company": "Itihad"}, "name")
		self.assertTrue(primary_identity)
		employee.custom_branches[1].left_position = 1
		employee.custom_branches[1].leaving_date = "2026-08-31"
		employee.save(ignore_permissions=True)
		departed = frappe.db.get_value("Employee", identity.name, ["status", "relieving_date"], as_dict=True)
		self.assertEqual(departed.status, "Left")
		self.assertEqual(str(departed.relieving_date), "2026-08-31")
		self.assertEqual(len(employee.custom_past_positions), 1)

	def test_profile_creates_revision_and_native_salary_assignment(self):
		frappe.set_user("Administrator")
		account = frappe.db.get_value("Account", {"company": "Itihad", "is_group": 0, "disabled": 0, "root_type": "Expense"}, "name")
		cost_center = frappe.db.get_value("Cost Center", {"company": "Itihad", "is_group": 0, "disabled": 0}, "name")
		employee = frappe.get_doc({
			"doctype": "Employee", "first_name": "Salary Profile Test", "gender": "Male",
			"date_of_birth": "1990-01-01", "date_of_joining": "2026-01-01",
			"status": "Active", "company": "Itihad",
			"custom_branches": [{"company": "Itihad", "branch": "Tripoli", "from_date": "2026-01-01"}],
		}).insert(ignore_permissions=True)
		profile = frappe.get_doc({
			"doctype": "Employee Salary Profile", "employee": employee.name,
			"effective_date": "2026-09-01", "action_date": "2026-08-25",
		})
		for fieldname, amount in (("basic_allocations", 1000), ("transportation_allocations", 200), ("family_allowance_allocations", 100)):
			profile.append(fieldname, {"company": "Itihad", "account": account, "cost_center": cost_center, "amount": amount, "percentage": 100})
		profile.insert(ignore_permissions=True)
		profile.basic_allocations[0].percentage = 90
		with self.assertRaises(frappe.ValidationError):
			profile._validate_allocations("Basic Salary", profile.basic_salary, "basic_allocations", {"Itihad"})
		profile.basic_allocations[0].percentage = 100
		payroll_employee = frappe.db.get_value("Employee", {"custom_master_employee": employee.name, "company": "Itihad"}, "name")
		revision = frappe.get_doc("Employee Salary Revision", profile.latest_revision)
		self.assertEqual(revision.total_salary, 1300)
		history = get_revision_history(profile.name)
		self.assertEqual(history[0].name, revision.name)
		self.assertEqual(len(history[0].allocations), 3)
		self.assertTrue(all(row.percentage == 100 for row in history[0].allocations))
		self.assertTrue(frappe.db.exists("Salary Structure Assignment", {"employee": payroll_employee, "from_date": "2026-09-01", "docstatus": 1}))
		payable = frappe.db.get_value("Account", {"company": "Itihad", "is_group": 0, "disabled": 0, "root_type": "Liability", "account_type": ["!=", "Payable"]}, "name")
		payroll = frappe.get_doc({
			"doctype": "Payroll Entry", "posting_date": "2026-09-30", "company": "Itihad",
			"start_date": "2026-09-01", "end_date": "2026-09-30", "payroll_frequency": "Monthly",
			"cost_center": cost_center, "currency": "USD", "exchange_rate": 1,
			"payroll_payable_account": payable, "employees": [{"employee": payroll_employee}],
		}).insert(ignore_permissions=True)
		slip = frappe.get_doc({
			"doctype": "Salary Slip", "employee": payroll_employee, "company": "Itihad",
			"posting_date": "2026-09-30", "start_date": "2026-09-01", "end_date": "2026-09-30",
			"payroll_frequency": "Monthly", "payroll_entry": payroll.name,
		}).insert(ignore_permissions=True)
		slip.submit()
		allocated = payroll.get_salary_component_total("earnings")
		self.assertAlmostEqual(allocated[(account, cost_center)], 1300)
		payroll.make_accrual_jv_entry([slip])
		journal = frappe.get_doc("Journal Entry", slip.reload().journal_entry)
		self.assertTrue(any(row.account == account and row.cost_center == cost_center for row in journal.accounts))
		payroll.append("custom_manual_deductions", {"employee": payroll_employee, "salary_component": "Professional Tax", "amount": 25, "note": "Test deduction"})
		payroll.save(ignore_permissions=True)
		create_manual_deductions(payroll)
		additional = frappe.get_doc("Additional Salary", payroll.custom_manual_deductions[0].additional_salary)
		self.assertEqual(additional.docstatus, 1)
		cancel_manual_deductions(payroll)
		self.assertEqual(frappe.db.get_value("Additional Salary", additional.name, "docstatus"), 2)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_hr_manager_cannot_access_salary_records_or_endpoint(self):
		frappe.set_user("hr@hr.hr")
		self.assertEqual(salary_query(), "1=0")
		self.assertFalse(salary_permission(None))
		self.assertFalse(frappe.has_permission("Employee Salary Profile", "read"))
		with self.assertRaises(frappe.PermissionError):
			get_salary_profile_summary("__missing_employee__")

	def test_accounts_manager_can_access_salary_records(self):
		frappe.set_user("l.harara@itihadorg.onmicrosoft.com")
		self.assertIsNone(salary_query())
		self.assertTrue(salary_permission(None))
		self.assertTrue(frappe.has_permission("Employee Salary Profile", "read"))
