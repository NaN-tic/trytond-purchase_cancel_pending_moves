# This file is part purchase_cancel_pending_moves module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest


from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import suite as test_suite


class PurchaseCancelPendingMovesTestCase(ModuleTestCase):
    'Test Purchase Cancel Pending Moves module'
    module = 'purchase_cancel_pending_moves'


def suite():
    suite = test_suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            PurchaseCancelPendingMovesTestCase))
    return suite
