# -*- encoding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError

class IrModelExportTemplate(models.Model):
    _inherit = 'ir.model.export.template'

    path = fields.Char('Path')
    filename = fields.Char('Filename')

    def download_export(self):
        param = self.env['ir.config_parameter'].search([('key', '=', 'web.base.url.export')], limit=1)
        if param:
            if self.path and self.filename:
                return {'type': 'ir.actions.act_url', 'url': param.value + '?id=' + str(self.id), 'target': 'self'}
            raise UserError(_('No file to download'))
        raise UserError(_('Please add key web.base.url.export to parameter'))
