# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection(selection_add=[('order_closed', "Order Closed")])
    close_order = fields.Boolean(default=False)

    @api.onchange('order_line')
    def _onchange_order_line(self):
        for record in self:
            lines = record.order_line
            products = lines.mapped('product_id')
            for product in products:
                order_line = lines.filtered(lambda r: r.product_id.id == product.id)
                if len(order_line) > 1:
                    raise ValidationError(_(
                        'Product : %s with reference %s has been added.') % (product.name, product.default_code))

    def _website_product_id_change_purchase(self, order_id, product_id, qty=0):
        res = super(PurchaseOrder, self)._website_product_id_change_purchase(
            order_id, product_id, qty=qty)
        product = self.env['product.template'].browse(product_id)
        if product.product_purchase_unit:
            res['purchase_unit'] = product.product_purchase_unit.id
        return res

    def _compute_amount_total_without_delivery_purchase(self):
        self.ensure_one()
        delivery_cost = sum(
            [l.price_total for l in self.order_line if l.is_delivery])
        return self.amount_untaxed - delivery_cost


    def close_ordering(self):
        for order in self:
            order.write({'close_order': True, 'state': 'order_closed'})

    def open_ordering(self):
        for order in self:
            order.write({'close_order': False, 'state': 'purchase'})
