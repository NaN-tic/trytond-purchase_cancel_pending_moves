import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear, create_tax,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Activate modules
        activate_modules('purchase_cancel_pending_moves')

        # Create company
        _ = create_company()
        company = get_company()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']
        cash = accounts['cash']
        Journal = Model.get('account.journal')
        PaymentMethod = Model.get('account.invoice.payment.method')
        cash_journal, = Journal.find([('type', '=', 'cash')])
        cash_journal.save()
        payment_method = PaymentMethod()
        payment_method.name = 'Cash'
        payment_method.journal = cash_journal
        payment_method.credit_account = cash
        payment_method.debit_account = cash
        payment_method.save()

        # Create tax
        tax = create_tax(Decimal('.10'))
        tax.save()

        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.customer_code = '1234'
        supplier.save()
        customer = Party(name='Customer')
        customer.save()

        # Create account categories
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()
        account_category_tax, = account_category.duplicate()
        account_category_tax.supplier_taxes.append(tax)
        account_category_tax.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.purchasable = True
        template.list_price = Decimal('10')
        template.account_category = account_category_tax
        template.save()
        product, = template.products
        template = ProductTemplate()
        template.name = 'service'
        template.default_uom = unit
        template.type = 'service'
        template.purchasable = True
        template.list_price = Decimal('30')
        template.account_category = account_category
        template.save()
        service, = template.products

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create an Inventory
        Inventory = Model.get('stock.inventory')
        Location = Model.get('stock.location')
        storage, = Location.find([
            ('code', '=', 'STO'),
        ])
        inventory = Inventory()
        inventory.location = storage
        inventory_line = inventory.lines.new(product=product)
        inventory_line.quantity = 100.0
        inventory_line.expected_quantity = 0.0
        inventory.click('confirm')
        self.assertEqual(inventory.state, 'done')

        # Purchase 5 products with an invoice method 'on shipment'
        Purchase = Model.get('purchase.purchase')
        PurchaseLine = Model.get('purchase.line')
        purchase = Purchase()
        purchase.party = supplier
        purchase.payment_term = payment_term
        purchase.invoice_method = 'shipment'
        purchase_line = PurchaseLine()
        purchase.lines.append(purchase_line)
        purchase_line.product = product
        purchase_line.quantity = 2.0
        purchase_line.unit_price = Decimal('10')
        purchase_line = PurchaseLine()
        purchase.lines.append(purchase_line)
        purchase_line.type = 'comment'
        purchase_line.description = 'Comment'
        purchase_line = PurchaseLine()
        purchase.lines.append(purchase_line)
        purchase_line.product = product
        purchase_line.quantity = 3.0
        purchase_line.unit_price = Decimal('10')
        purchase_line = PurchaseLine()
        purchase.lines.append(purchase_line)
        purchase_line.product = product
        purchase_line.quantity = -3.0
        purchase_line.unit_price = Decimal('10')
        purchase.click('quote')
        purchase.click('confirm')
        self.assertEqual(purchase.state, 'processing')
        self.assertEqual(purchase.shipment_state, 'waiting')
        self.assertEqual(purchase.invoice_state, 'none')
        purchase.reload()
        self.assertEqual(len(purchase.moves), 3)

        self.assertEqual(len(purchase.shipments), 0)

        self.assertEqual(len(purchase.shipment_returns), 1)

        self.assertEqual(len(purchase.invoices), 0)

        # Cancel Pending moves
        purchase.click('cancel_pending_moves')
        self.assertEqual(purchase.state, 'done')
        self.assertEqual(purchase.shipment_state, 'received')
        self.assertEqual(purchase.invoice_state, 'none')
