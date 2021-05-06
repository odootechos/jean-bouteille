# coding: utf-8


from odoo import models, fields, api, _


class ResPartner(models.Model):
	_inherit = 'res.partner'

	facebook_url = fields.Char(_('Facebook URL'))
	fax = fields.Char(_('Fax'))
	purchase_code = fields.Char(_('Supplier code'))
	sale_code = fields.Char(_('Sale code'))

	partner_network_id = fields.Many2one('res.partner.network', string=_('Network'))


class ResPartnerNetwork(models.Model):
	_name = 'res.partner.network'
	_description = _('Partner network')

	name = fields.Char(_('Name'))
