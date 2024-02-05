=================
Purchase Scenario
=================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import Model, Wizard, Report
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()

Activate modules::

    >>> config = activate_modules('purchase_cancel_pending_moves')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> cash = accounts['cash']

    >>> Journal = Model.get('account.journal')
    >>> PaymentMethod = Model.get('account.invoice.payment.method')
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.save()
    >>> payment_method = PaymentMethod()
    >>> payment_method.name = 'Cash'
    >>> payment_method.journal = cash_journal
    >>> payment_method.credit_account = cash
    >>> payment_method.debit_account = cash
    >>> payment_method.save()

Create tax::

    >>> tax = create_tax(Decimal('.10'))
    >>> tax.save()

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.customer_code = '1234'
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create account categories::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.save()

    >>> account_category_tax, = account_category.duplicate()
    >>> account_category_tax.supplier_taxes.append(tax)
    >>> account_category_tax.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')

    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.list_price = Decimal('10')
    >>> template.account_category = account_category_tax
    >>> template.save()
    >>> product, = template.products

    >>> template = ProductTemplate()
    >>> template.name = 'service'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.purchasable = True
    >>> template.list_price = Decimal('30')
    >>> template.account_category = account_category
    >>> template.save()
    >>> service, = template.products

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create an Inventory::

    >>> Inventory = Model.get('stock.inventory')
    >>> Location = Model.get('stock.location')
    >>> storage, = Location.find([
    ...         ('code', '=', 'STO'),
    ...         ])
    >>> inventory = Inventory()
    >>> inventory.location = storage
    >>> inventory_line = inventory.lines.new(product=product)
    >>> inventory_line.quantity = 100.0
    >>> inventory_line.expected_quantity = 0.0
    >>> inventory.click('confirm')
    >>> inventory.state
    'done'

Purchase 5 products with an invoice method 'on shipment'::

    >>> Purchase = Model.get('purchase.purchase')
    >>> PurchaseLine = Model.get('purchase.line')
    >>> purchase = Purchase()
    >>> purchase.party = supplier
    >>> purchase.payment_term = payment_term
    >>> purchase.invoice_method = 'shipment'
    >>> purchase_line = PurchaseLine()
    >>> purchase.lines.append(purchase_line)
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 2.0
    >>> purchase_line.unit_price = Decimal('10')
    >>> purchase_line = PurchaseLine()
    >>> purchase.lines.append(purchase_line)
    >>> purchase_line.type = 'comment'
    >>> purchase_line.description = 'Comment'
    >>> purchase_line = PurchaseLine()
    >>> purchase.lines.append(purchase_line)
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 3.0
    >>> purchase_line.unit_price = Decimal('10')
    >>> purchase_line = PurchaseLine()
    >>> purchase.lines.append(purchase_line)
    >>> purchase_line.product = product
    >>> purchase_line.quantity = -3.0
    >>> purchase_line.unit_price = Decimal('10')
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'
    >>> purchase.shipment_state
    'waiting'
    >>> purchase.invoice_state
    'none'
    >>> purchase.reload()
    >>> len(purchase.moves), len(purchase.shipments), len(purchase.shipment_returns), len(purchase.invoices)
    (3, 0, 1, 0)

Cancel Pending moves::

    >>> purchase.click('cancel_pending_moves')
    >>> purchase.state
    'done'
    >>> purchase.shipment_state
    'none'
    >>> purchase.invoice_state
    'none'
