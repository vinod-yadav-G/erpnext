# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.tests.utils import FrappeTestCase, if_app_installed
from frappe.utils import add_days, today

from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
from erpnext.selling.doctype.customer.test_customer import get_customer_dict
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.report.sales_analytics.sales_analytics import execute


class TestAnalytics(FrappeTestCase):
	def setUp(self):
		item = make_test_item("__Test Analytics Item")
		customer = frappe.get_doc(get_customer_dict("__Test Analytics Customer")).insert(
			ignore_permissions=True
		)
		self.item_code = item.item_code
		self.customer = customer.name

		self.filters = {
			"tree_type": "Item Group",
			"doc_type": "Sales Order",
			"value_quantity": "Value",
			"from_date": add_days(today(), 2),
			"to_date": add_days(today(), 2),
			"range": "Monthly",
		}

	def tearDown(self):
		frappe.db.rollback()

	def test_sales_analytics(self):
		frappe.db.sql("delete from `tabSales Order` where company='_Test Company 2'")

		create_sales_orders()

		self.compare_result_for_customer()
		self.compare_result_for_customer_group()
		self.compare_result_for_customer_based_on_quantity()

	def test_report_sales_analytics(self):
		so = make_sales_order(
			customer=self.customer,
			item_code=self.item_code,
			transaction_date=add_days(today(), 2),
			do_not_save=True,
		)
		so.insert(ignore_permissions=True)
		so.submit()

		self.filters["company"] = so.company
		data = execute(self.filters)
		self.assertEqual(data[1][0].get("entity"), "All Item Groups")

		self.filters.update({"tree_type": "Order Type"})
		report = execute(self.filters)
		if report[1]:
			for row in report[1]:
				if row.get("entity") == "Order Types":
					self.assertEqual(row.get("total"), 1000)

	@if_app_installed("projects")
	def test_sales_analytics_report_with_project(self):
		so = make_sales_order(
			customer=self.customer,
			item_code=self.item_code,
			transaction_date=add_days(today(), 2),
			do_not_save=True,
		)
		so.project = get_project()
		so.insert(ignore_permissions=True)
		so.submit()

		self.filters.update({"tree_type": "Project", "company": so.company})
		report = execute(self.filters)
		if report[1]:
			for row in report[1]:
				if row.get("entity") == get_project():
					self.assertTrue(row.get("entity"), "Test Sales Analytics Project")
					self.assertTrue(row.get("total"), 1000)

	def compare_result_for_customer(self):
		filters = {
			"doc_type": "Sales Order",
			"range": "Monthly",
			"to_date": "2018-03-31",
			"tree_type": "Customer",
			"company": "_Test Company 2",
			"from_date": "2017-04-01",
			"value_quantity": "Value",
		}

		report = execute(filters)

		expected_data = [
			{
				"entity": "_Test Customer 1",
				"entity_name": "_Test Customer 1",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"oct_2017": 0.0,
				"sep_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 2000.0,
				"mar_2018": 0.0,
				"total": 2000.0,
			},
			{
				"entity": "_Test Customer 2",
				"entity_name": "_Test Customer 2",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"sep_2017": 1500.0,
				"oct_2017": 1000.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 2500.0,
			},
			{
				"entity": "_Test Customer 3",
				"entity_name": "_Test Customer 3",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 2000.0,
				"jul_2017": 1000.0,
				"aug_2017": 0.0,
				"sep_2017": 0.0,
				"oct_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 3000.0,
			},
		]
		result = sorted(report[1], key=lambda k: k["entity"])
		self.assertEqual(expected_data, result)

	def compare_result_for_customer_group(self):
		filters = {
			"doc_type": "Sales Order",
			"range": "Monthly",
			"to_date": "2018-03-31",
			"tree_type": "Customer Group",
			"company": "_Test Company 2",
			"from_date": "2017-04-01",
			"value_quantity": "Value",
		}

		report = execute(filters)

		expected_first_row = {
			"entity": "All Customer Groups",
			"indent": 0,
			"apr_2017": 0.0,
			"may_2017": 0.0,
			"jun_2017": 2000.0,
			"jul_2017": 1000.0,
			"aug_2017": 0.0,
			"sep_2017": 1500.0,
			"oct_2017": 1000.0,
			"nov_2017": 0.0,
			"dec_2017": 0.0,
			"jan_2018": 0.0,
			"feb_2018": 2000.0,
			"mar_2018": 0.0,
			"total": 7500.0,
		}
		self.assertEqual(expected_first_row, report[1][0])

	def compare_result_for_customer_based_on_quantity(self):
		filters = {
			"doc_type": "Sales Order",
			"range": "Monthly",
			"to_date": "2018-03-31",
			"tree_type": "Customer",
			"company": "_Test Company 2",
			"from_date": "2017-04-01",
			"value_quantity": "Quantity",
		}

		report = execute(filters)

		expected_data = [
			{
				"entity": "_Test Customer 1",
				"entity_name": "_Test Customer 1",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"sep_2017": 0.0,
				"oct_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 20.0,
				"mar_2018": 0.0,
				"total": 20.0,
			},
			{
				"entity": "_Test Customer 2",
				"entity_name": "_Test Customer 2",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"sep_2017": 15.0,
				"oct_2017": 10.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 25.0,
			},
			{
				"entity": "_Test Customer 3",
				"entity_name": "_Test Customer 3",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 20.0,
				"jul_2017": 10.0,
				"aug_2017": 0.0,
				"sep_2017": 0.0,
				"oct_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 30.0,
			},
		]
		result = sorted(report[1], key=lambda k: k["entity"])
		self.assertEqual(expected_data, result)


def create_sales_orders():
	frappe.set_user("Administrator")

	make_sales_order(
		company="_Test Company 2",
		qty=10,
		customer="_Test Customer 1",
		transaction_date="2018-02-10",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)

	make_sales_order(
		company="_Test Company 2",
		qty=10,
		customer="_Test Customer 1",
		transaction_date="2018-02-15",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)

	make_sales_order(
		company="_Test Company 2",
		qty=10,
		customer="_Test Customer 2",
		transaction_date="2017-10-10",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)

	make_sales_order(
		company="_Test Company 2",
		qty=15,
		customer="_Test Customer 2",
		transaction_date="2017-09-23",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)

	make_sales_order(
		company="_Test Company 2",
		qty=20,
		customer="_Test Customer 3",
		transaction_date="2017-06-15",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)

	make_sales_order(
		company="_Test Company 2",
		qty=10,
		customer="_Test Customer 3",
		transaction_date="2017-07-10",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)


def get_project():
	project_name = "Test Sales Analytics Project"

	if not frappe.db.exists("Project", {"project_name": project_name}):
		frappe.get_doc(
			{"doctype": "Project", "project_name": project_name, "company": "_Test Company"}
		).insert(ignore_permissions=True, set_name=project_name)

	return project_name
