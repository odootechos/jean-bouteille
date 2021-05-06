# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends('picking_id')
    def _calculate_price_uom(self):
        for move in self:
            unit_measure = move.product_id.uom_id.name
            if not isinstance(move.id, models.NewId):
                move_line = self.env['stock.move'].search([('id', '=', move.id)], limit=1)
                if move_line.sale_line_id:
                    order_line = self.env['sale.order.line'].search([('id', '=', move_line.sale_line_id.id)])
                    unit_measure = order_line.product_uom.name
                if move_line.purchase_line_id:
                    purchase_line = self.env['purchase.order.line'].search([('id', '=', move_line.purchase_line_id.id)])
                    unit_measure = purchase_line.product_uom.name
            move.unit_measure = unit_measure

    unit_measure = fields.Char(
        string='Unit Measure Calculated',
        compute=_calculate_price_uom,
        store=False
    )
    uom_value = fields.Char(
        string='Unit Measure',
        related='unit_measure',
        store=True
    )
