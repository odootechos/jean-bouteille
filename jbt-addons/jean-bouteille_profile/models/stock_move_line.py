# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    total_qty_done = fields.Float(
        'Total Quantity Calculated',
        compute='_compute_total_qty',
        store=False)
    qty_done_total = fields.Float(
        'Total Quantity',
        related='total_qty_done')
    flag = fields.Boolean(
        string='Flag',
        default=False
    )

    @api.depends('product_id', 'qty_done')
    def _compute_total_qty(self):
        for move in self:
            move.total_qty_done = 0.0
            if move.product_id and move.qty_done:
                if move.product_id.product_tmpl_id.uom_id:
                    if move.product_id.product_tmpl_id.uom_id.uom_type == 'reference':
                        move.qty_done_total = move.qty_done
                    else:
                        move.qty_done_total = move.qty_done * 1 / move.product_id.product_tmpl_id.uom_id.factor
                else:
                    move.qty_done_total = move.qty_done
                move.total_qty_done = move.qty_done_total

    @api.constrains('lot_id', 'product_id')
    def _check_lot_product(self):
        return True
