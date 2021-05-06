# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, api, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    invoice_status = fields.Selection(selection_add=[('not to invoice', "Not To Invoice")])
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

    def _website_product_id_change(self, order_id, product_id, qty=0):
        res = super(SaleOrder, self)._website_product_id_change(
            order_id, product_id, qty=qty)
        product = self.env['product.product'].browse(product_id)
        if product.so_unit:
            res['product_uom'] = product.so_unit.id
        return res

    def _compute_amount_total_without_delivery(self):
        self.ensure_one()
        delivery_cost = sum(
            [l.price_total for l in self.order_line if l.is_delivery])
        return self.amount_untaxed - delivery_cost

    @api.depends('product_id')
    def onchange_product_uom(self):
        for record in self:
            if record.order_line.product_id.product_tmpl_id.so_unit:
                record.order_line.product_uom = record.order_line.product_id.product_tmpl_id.so_unit
            else:
                record.order_line.product_uom = record.order_line.product_id.product_tmpl_id.uom_id

    def close_ordering(self):
        for order in self:
            order.write({'close_order': True, 'invoice_status': 'not to invoice', 'state': 'order_closed'})

    def open_ordering(self):
        for order in self:
            order.write({'close_order': False, 'invoice_status': 'no', 'state': 'sale'})

    @api.depends('state', 'order_line.invoice_status', 'order_line.invoice_lines')
    def _get_invoiced(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.

        The invoice_ids are obtained thanks to the invoice lines of the SO lines, and we also search
        for possible refunds created directly from existing invoices. This is necessary since such a
        refund is not directly linked to the SO.
        """
        # Ignore the status of the deposit product
        deposit_product_id = self.env['sale.advance.payment.inv']._default_product_id()
        line_invoice_status_all = [(d['order_id'][0], d['invoice_status']) for d in
                                   self.env['sale.order.line'].read_group([('order_id', 'in', self.ids),
                                                                           ('product_id', '!=', deposit_product_id.id)],
                                                                          ['order_id', 'invoice_status'],
                                                                          ['order_id', 'invoice_status'], lazy=False)]
        for order in self:
            print(order.invoice_status)
            invoice_ids = order.order_line.mapped('invoice_lines').mapped('move_id')\
                .filtered(lambda r: r.move_type in ['out_invoice', 'out_refund'])
            # Search for invoices which have been 'cancelled' (filter_refund = 'modify' in
            # 'account.invoice.refund')
            # use like as origin may contains multiple references (e.g. 'SO01, SO02')
            refunds = invoice_ids.search([
                ('invoice_origin', 'like', order.name),
                ('company_id', '=', order.company_id.id),
                ('move_type', 'in', ('out_invoice', 'out_refund'))])
            invoice_ids |= refunds.filtered(lambda r: order.name in [origin.strip() for origin in r.invoice_origin.split(',')])

            # Search for refunds as well
            domain_inv = expression.OR([
                ['&', ('invoice_origin', '=', inv.number), ('journal_id', '=', inv.journal_id.id)]
                for inv in invoice_ids if inv.number
            ])
            if domain_inv:
                refund_ids = self.env['account.move'].search(expression.AND([
                    ['&', ('move_type', '=', 'out_refund'), ('invoice_origin', '!=', False)],
                    domain_inv
                ]))
            else:
                refund_ids = self.env['account.move'].browse()

            line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == order.id]
            if order.close_order is True:
                invoice_status = 'not to invoice'
            else:
                if order.state not in ('sale', 'done'):
                    invoice_status = 'no'
                elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                    invoice_status = 'to invoice'
                elif all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                    invoice_status = 'invoiced'
                elif all(invoice_status in ['invoiced', 'upselling'] for invoice_status in line_invoice_status):
                    invoice_status = 'upselling'
                else:
                    invoice_status = 'no'
            order.update({
                'invoice_count': len(set(invoice_ids.ids + refund_ids.ids)),
                'invoice_ids': invoice_ids.ids + refund_ids.ids,
                'invoice_status': invoice_status
            })
