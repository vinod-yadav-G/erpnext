# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, today

from erpnext.accounts.report.purchase_register.purchase_register import execute


class TestPurchaseRegister(FrappeTestCase):
	def test_purchase_register(self):
		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company 6'")
		frappe.db.sql("delete from `tabGL Entry` where company='_Test Company 6'")

		filters = frappe._dict(company="_Test Company 6", from_date=add_months(today(), -1), to_date=today())

		pi = make_purchase_invoice()

		report_results = execute(filters)
		first_row = frappe._dict(report_results[1][0])
		self.assertEqual(first_row.voucher_type, "Purchase Invoice")
		self.assertEqual(first_row.voucher_no, pi.name)
		self.assertEqual(first_row.payable_account, "Creditors - _TC6")
		self.assertEqual(first_row.net_total, 1000)
		self.assertEqual(first_row.total_tax, 100)
		self.assertEqual(first_row.grand_total, 1100)

	def test_purchase_register_ledger_view(self):
		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company 6'")
		frappe.db.sql("delete from `tabGL Entry` where company='_Test Company 6'")

		filters = frappe._dict(
			company="_Test Company 6",
			from_date=add_months(today(), -1),
			to_date=today(),
			include_payments=True,
			supplier="_Test Supplier",
		)

		make_purchase_invoice()
		pe = make_payment_entry()

		report_results = execute(filters)
		first_row = frappe._dict(report_results[1][2])
		self.assertEqual(first_row.voucher_type, "Payment Entry")
		self.assertEqual(first_row.voucher_no, pe.name)
		self.assertEqual(first_row.payable_account, "Creditors - _TC6")
		self.assertEqual(first_row.debit, 0)
		self.assertEqual(first_row.credit, 600)
		self.assertEqual(first_row.balance, 500)

	def test_validate_supplier_codecov(self):
		filters = frappe._dict(
			from_date=add_months(today(), -1),
			to_date=today(),
			include_payments=True,
		)
		with self.assertRaises(frappe.ValidationError) as e:
			execute(filters)
		self.assertIn("Please select a supplier for fetching payments.", str(e.exception))

	def test_purchase_register_basic_codecov(self):
		"""Ensure purchase register returns invoices for _Test Company"""
		filters = frappe._dict(
			company="_Test Company",
			from_date=add_months(today(), -1),
			to_date=today(),
		)

		columns, data = execute(filters)[:2]

		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)

		# There should be at least one purchase invoice in test data
		self.assertTrue(any(d.get("voucher_type") == "Purchase Invoice" for d in data))

	def test_purchase_register_with_supplier_codecov(self):
		"""Filter purchase register by supplier"""

		filters = frappe._dict(
			company="_Test Company",
			supplier="_Test Supplier",
			from_date=add_months(today(), -1),
			to_date=today(),
		)

		_, data = execute(filters)[:2]

		self.assertTrue(all(d.get("supplier_id") == "_Test Supplier" for d in data))

	def test_purchase_register_with_payments_codecov(self):
		filters = frappe._dict(
			company="_Test Company",
			supplier="_Test Supplier",
			from_date=add_months(today(), -1),
			to_date=today(),
			include_payments=1,
		)

		columns, data = execute(filters)[:2]

		# Payments should add debit/credit fields
		self.assertIn("debit", columns[0].keys() or {})
		self.assertIn("credit", columns[0].keys() or {})

		# At least one row should contain balance
		self.assertTrue(any("balance" in row for row in data))

	def test_purchase_register_with_mode_of_payment_codecov(self):
		pi = make_purchase_invoice()
		filters = frappe._dict(
			company="_Test Company 6",
			from_date=add_months(today(), -1),
			to_date=today(),
			mode_of_payment=pi.mode_of_payment,
		)

		_, data = execute(filters)[:2]
		self.assertTrue(all(d.get("mode_of_payment") == pi.mode_of_payment for d in data))

	def test_purchase_register_no_invoices_codecov(self):
		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company 6'")

		filters = frappe._dict(
			company="_Test Company 6",
			from_date=today(),
			to_date=today(),
		)

		columns, data = execute(filters)[:2]
		self.assertEqual(data, [])

	def test_purchase_register_internal_supplier_codecov(self):
		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"supplier": "_Test Supplier",
				"company": "_Test Company 6",
				"represents_company": "_Test Company 6",
				"is_internal_supplier": 1,
				"posting_date": today(),
				"credit_to": "Creditors - _TC6",
				"items": [
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 500,
						"expense_account": "Stock Received But Not Billed - _TC6",
						"cost_center": "Main - _TC6",
					}
				],
			}
		)
		pi.submit()

		filters = frappe._dict(company="_Test Company 6", from_date=add_months(today(), -1), to_date=today())
		_, data = execute(filters)[:2]

		self.assertFalse(any("unrealized" in key for row in data for key in row.keys()))

	def test_purchase_register_with_po_pr_codecov(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		po = create_purchase_order(company="_Test Company", supplier="_Test Supplier")
		pr = make_purchase_receipt(po.name)

		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"supplier": "_Test Supplier",
				"company": "_Test Company",
				"posting_date": today(),
				"credit_to": "Creditors - _TC",
				"items": [
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 200,
						"purchase_order": po.name,
						"purchase_receipt": pr.name,
						"expense_account": "Stock Received But Not Billed - _TC",
						"cost_center": "_Test Cost Center - _TC",
					}
				],
			}
		)
		pi.submit()

		filters = frappe._dict(company="_Test Company", from_date=add_months(today(), -1), to_date=today())
		_, data = execute(filters)[:2]

		self.assertTrue(any(row.get("purchase_order") for row in data))
		self.assertTrue(any(row.get("purchase_receipt") for row in data))

	def test_purchase_register_payments_without_invoices_codecov(self):
		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company 6'")

		make_payment_entry()

		filters = frappe._dict(
			company="_Test Company 6",
			supplier="_Test Supplier",
			from_date=add_months(today(), -1),
			to_date=today(),
			include_payments=True,
		)

		_, data = execute(filters)[:2]
		self.assertTrue(any(d.get("voucher_type") == "Payment Entry" for d in data))


def make_purchase_invoice():
	from erpnext.accounts.doctype.account.test_account import create_account
	from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	create_account(
		account_name="GST",
		account_type="Tax",
		parent_account="Duties and Taxes - _TC6",
		company="_Test Company 6",
		account_currency="INR",
	)
	create_warehouse(warehouse_name="_Test Warehouse - _TC6", company="_Test Company 6")
	create_cost_center(cost_center_name="_Test Cost Center", company="_Test Company 6")
	pi = create_purchase_invoice_with_taxes()
	pi.submit()
	return pi


def create_purchase_invoice_with_taxes():
	return frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"posting_date": today(),
			"supplier": "_Test Supplier",
			"company": "_Test Company 6",
			"cost_center": "_Test Cost Center - _TC6",
			"taxes_and_charges": "",
			"currency": "INR",
			"credit_to": "Creditors - _TC6",
			"items": [
				{
					"doctype": "Purchase Invoice Item",
					"cost_center": "_Test Cost Center - _TC6",
					"item_code": "_Test Item",
					"qty": 1,
					"rate": 1000,
					"expense_account": "Stock Received But Not Billed - _TC6",
				}
			],
			"taxes": [
				{
					"account_head": "GST - _TC6",
					"cost_center": "_Test Cost Center - _TC6",
					"add_deduct_tax": "Add",
					"category": "Valuation and Total",
					"charge_type": "Actual",
					"description": "Shipping Charges",
					"doctype": "Purchase Taxes and Charges",
					"parentfield": "taxes",
					"rate": 100,
					"tax_amount": 100.0,
				}
			],
		}
	)


def make_payment_entry():
	frappe.set_user("Administrator")
	from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

	return create_payment_entry(
		company="_Test Company 6",
		party_type="Supplier",
		party="_Test Supplier",
		payment_type="Pay",
		paid_from="Cash - _TC6",
		paid_to="Creditors - _TC6",
		paid_amount=600,
		save=1,
		submit=1,
	)
