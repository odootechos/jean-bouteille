# coding: utf-8

from odoo import models


class SaleOrder(models.Model):
	_inherit = 'sale.order'

	def action_confirm(self):
		super(SaleOrder, self).action_confirm()
		for sale in self:
			sale.partner_id.prospect = 'customer'
			sale.partner_invoice_id.prospect = 'customer'
			sale.partner_shipping_id.prospect = 'customer'
