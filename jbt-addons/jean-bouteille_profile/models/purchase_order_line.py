# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    discount = fields.Float(
        'Discount (%)', digits=dp.get_precision('Discount'))

    @api.onchange('product_id')
    def onchange_product_uom(self):
        for record in self:
            if record.product_id.product_tmpl_id.product_purchase_unit:
                record.product_uom = record.product_id.product_tmpl_id.product_purchase_unit
            else:
                record.product_uom = record.product_id.product_tmpl_id.uom_id

            record.price_subtotal = (record.price_unit * record.product_uom.factor_inv) * record.product_qty
