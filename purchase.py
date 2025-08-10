# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, Not
from trytond.transaction import Transaction


class Purchase(metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

    pending_moves = fields.Function(fields.Many2Many('stock.move', None, None,
            'Pending Moves'), 'get_pending_moves', setter='set_pending_moves')

    @classmethod
    def __setup__(cls):
        super(Purchase, cls).__setup__()
        cls._buttons.update({
                'cancel_pending_moves': {
                    'invisible': Not(Bool(Eval('pending_moves'))),
                    },
                })

    @classmethod
    @ModelView.button
    def cancel_pending_moves(cls, purchases):
        pool = Pool()
        StockMove = pool.get('stock.move')
        ShipmentIn = pool.get('stock.shipment.in')
        ShipmentInReturn = pool.get('stock.shipment.in.return')
        HandleShipmentException = pool.get(
            'purchase.handle.shipment.exception', type='wizard')

        for purchase in purchases:
            pending_moves = purchase.pending_moves
            StockMove.cancel(pending_moves)

            with Transaction().set_context(active_model=cls.__name__,
                    active_ids=[purchase.id], active_id=purchase.id):
                session_id, _, _ = HandleShipmentException.create()
                handle_shipment_exception = HandleShipmentException(session_id)
                handle_shipment_exception.ask.recreate_moves = []
                handle_shipment_exception.ask.domain_moves = pending_moves
                handle_shipment_exception.transition_handle()
                HandleShipmentException.delete(session_id)

            shipments = []
            for shipment in purchase.shipments:
                if not any([x.state != 'cancelled' for x in shipment.moves]):
                    shipments.append(shipment)
            if shipments:
                ShipmentIn.cancel(shipments)

            shipments = []
            for shipment in purchase.shipment_returns:
                if not any([x.state != 'cancelled' for x in shipment.moves]):
                    shipments.append(shipment)
            if shipments:
                ShipmentInReturn.cancel(shipments)

    @classmethod
    def get_pending_moves(cls, purchases, name=None):
        result = dict((p.id, []) for p in purchases)

        for purchase in purchases:
            for line in purchase.lines:
                result[purchase.id].extend([m.id for m in line.pending_moves])
        return result

    @classmethod
    def set_pending_moves(cls, purchases, name, value):
        pass


class PurchaseLine(metaclass=PoolMeta):
    __name__ = 'purchase.line'
    pending_moves = fields.Function(fields.Many2Many('stock.move', None, None,
            'Pending Moves'), 'get_pending_moves')

    @classmethod
    def get_pending_moves(cls, lines, name):
        pending_moves = {}
        for line in lines:
            moves = []
            skip = set(line.moves_ignored + line.moves_recreated)
            for move in line.moves:
                if move.state not in ('cancel', 'done') and move not in skip:
                    moves.append(move.id)
            pending_moves[line.id] = moves

        return pending_moves
