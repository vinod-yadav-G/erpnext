# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
from frappe.tests.utils import FrappeTestCase


class TestWBSMonthlyDistribution(FrappeTestCase):
	def setUp(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()

	def tearDown(self):
		frappe.db.rollback()

	def test_check_duplicate_for_wbs(self):
		project_name = "test_project" + frappe.generate_hash(length=5)
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert()

		project = frappe.db.get_value("Project", {"project_name": project_name})

		wbs = frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"project": project or "_T-Project-00001",
				"wbs_name": f"test_wbs_{frappe.generate_hash(length=5)}",
				"company": "_Test Company",
				"gl_account": "Cash - _TC",
			}
		)
		wbs.insert()

		frappe.db.delete("WBS Monthly Distribution", {"for_wbs": wbs.name})

		wbs_monthly_distribution = frappe.get_doc(
			{"doctype": "WBS Monthly Distribution", "for_wbs": wbs.name}
		)
		wbs_monthly_distribution.insert()
		print(wbs_monthly_distribution.name, "11111111111111111111111111111111111111")

		wbs_monthly_distribution1 = frappe.get_doc(
			{"doctype": "WBS Monthly Distribution", "for_wbs": wbs.name}
		)

		with self.assertRaises(frappe.exceptions.ValidationError) as context:
			wbs_monthly_distribution1.insert()

		error_message = str(context.exception)
		self.assertIn("A record with the same WBS already exists", error_message)

	def test_wbs_monthly_distribution_update_linked_wbs(self):
		project_name = "test_project" + frappe.generate_hash(length=5)
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert()

		project = frappe.db.get_value("Project", {"project_name": project_name})

		wbs = frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"project": project or "_T-Project-00001",
				"wbs_name": f"test_wbs_{frappe.generate_hash(length=5)}",
				"company": "_Test Company",
				"gl_account": "Cash - _TC",
			}
		)
		wbs.insert()
		wbs.submit()
		self.assertEqual(wbs.docstatus, 1)

		wbs_monthly_distributuon = frappe.get_doc(
			{"doctype": "WBS Monthly Distribution", "for_wbs": wbs.name}
		)
		wbs_monthly_distributuon.insert()
		print(wbs_monthly_distributuon.name, "2222222222222222222222222222")
		wbs.load_from_db()
		self.assertEqual(wbs.linked_monthly_distribution, wbs_monthly_distributuon.name)

		wbs_monthly_distributuon.delete()
		wbs.load_from_db()
		self.assertIsNone(wbs.linked_monthly_distribution)

	def test_check_total_allocation(self):
		project_name = "test_project" + frappe.generate_hash(length=5)
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert()

		project = frappe.db.get_value("Project", {"project_name": project_name})

		def create_wbs(name_suffix):
			wbs = frappe.get_doc(
				{
					"doctype": "Work Breakdown Structure",
					"project": project or "_T-Project-00001",
					"wbs_name": f"test_wbs_{frappe.generate_hash(length=5)}",
					"company": "_Test Company",
					"gl_account": "Cash - _TC",
				}
			)
			wbs.insert()
			wbs.submit()
			return wbs

		child_meta = frappe.get_meta("Distribution Percentage")
		has_month_field = any(df.fieldname == "month" for df in child_meta.fields)

		valid_months = [
			"January",
			"February",
			"March",
			"April",
			"May",
			"June",
			"July",
			"August",
			"September",
			"October",
			"November",
			"December",
		]

		def make_distribution_rows(values):
			rows = []
			for i, val in enumerate(values):
				row = {"allocation": val}
				if has_month_field:
					row["month"] = valid_months[i % 12]
				rows.append(row)
			return rows

		wbs_valid = create_wbs("valid")
		valid_distribution = frappe.get_doc(
			{
				"doctype": "WBS Monthly Distribution",
				"for_wbs": wbs_valid.name,
				"monthly_distribution": make_distribution_rows([60, 40]),
			}
		)
		valid_distribution.insert()
		print(valid_distribution.name, "33333333333333333333333333333333")
		self.assertTrue(valid_distribution.name)

		wbs_invalid = create_wbs("invalid")
		invalid_distribution = frappe.get_doc(
			{
				"doctype": "WBS Monthly Distribution",
				"for_wbs": wbs_invalid.name,
				"monthly_distribution": make_distribution_rows([60, 50]),
			}
		)

		with self.assertRaises(frappe.exceptions.ValidationError) as context:
			invalid_distribution.insert()

		self.assertIn(
			"Total Monthly Distribution Allocation Percentage should not be more than 100%",
			str(context.exception),
		)
