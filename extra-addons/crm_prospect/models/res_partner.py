# coding: utf-8

from odoo import models, fields, api, _


class ResPartner(models.Model):
	_inherit = 'res.partner'

	prospect = fields.Selection([('prospect', _('Prospect')), ('customer', _('Customer'))], default='prospect', string=_('Is a prospect'))

	@api.model
	def _default_ref(self): 
		return  self.env['ir.sequence'].next_by_code('res_partner.ref')

	ref = fields.Char(string='Internal Reference', index=True, default=lambda self: self._default_ref())
 