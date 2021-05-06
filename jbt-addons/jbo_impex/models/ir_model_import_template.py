# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import fields, models


class IrModelImportTemplate(models.Model):
    _inherit = 'ir.model.import.template'

    sequence = fields.Integer('Sequence')
    id_current_import = fields.Integer("Current import")

    def create_cron(self, **kwargs):
        for record in self:
            date = fields.Datetime.now().strftime('%Y-%m-%d 17:00:00')
            kwargs.update({'priority': record.sequence, 'nextcall': fields.Datetime.from_string(date)})
            super(IrModelImportTemplate, record).create_cron(**kwargs)
        return True

    def _create_import(self, *args):
        vals = self._get_import_vals(*args)
        res = self.env['ir.model.import'].create(vals)  
        self._cr.execute("update ir_model_import_template set id_current_import={0} where id={1}".format(res.id, self.id))
        self._cr.execute("""
            insert into error_history(current_import_id,error_occured)
            values({},false)
            """.format(res.id))
        return res     

class ErrorHistory(models.Model):
    _name = 'error.history'

    current_import_id = fields.Many2one("ir.model.import", string='Current import')
    error_occured = fields.Boolean(string='Error occured', default=False)

