# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    reserved_qty_total = fields.Float(
        'Total Quantity Reserved Calculated',
        compute='_compute_total_reserved_qty',
        store=False)
    total_reserved_qty = fields.Float(
        'Total Quantity Reserved',
        related='reserved_qty_total',
        store=True)
    qty_total = fields.Float(
        'Total Quantity Calculated',
        compute='_compute_total_qty',
        store=False)
    total_qty = fields.Float(
        'Total Quantity',
        related='qty_total',
        store=True)

    @api.depends('product_id', 'quantity')
    def _compute_total_qty(self):
        for quant in self:
            quant.qty_total = 0.0
            if quant.product_id and quant.quantity:
                if quant.product_tmpl_id.uom_id:
                    if quant.product_tmpl_id.uom_id.uom_type == 'reference':
                        quant.qty_total = quant.quantity
                    else:
                        quant.qty_total = quant.quantity * 1 / quant.product_id.uom_id.factor
                else:
                    quant.qty_total = quant.quantity

    @api.depends('product_tmpl_id', 'reserved_quantity')
    def _compute_total_reserved_qty(self):
        for quant in self:
            quant.reserved_qty_total = 0.0
            if quant.product_tmpl_id and quant.reserved_quantity:
                if quant.product_id.uom_id:
                    if quant.product_tmpl_id.uom_id.uom_type == 'reference':
                        quant.qty_total = quant.quantity
                    else:
                        quant.reserved_qty_total = quant.reserved_quantity * 1 / quant.product_id.uom_id.factor
                else:
                    quant.reserved_qty_total = quant.reserved_quantity