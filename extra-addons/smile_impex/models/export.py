# -*- coding: utf-8 -*-
# (C) 2014 Smile (<http://www.smile.fr>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.modules.registry import Registry
from odoo.tools.safe_eval import safe_eval

from odoo.addons.smile_impex.models.impex import state_cleaner


class IrModelExport(models.Model):
    _name = 'ir.model.export'
    _description = 'Export'
    _inherit = 'ir.model.impex'

    def __init__(self, pool, cr):
        super(IrModelExport, self).__init__(pool, cr)
        model = pool[self._name]
        if not getattr(model, '_state_cleaner', False):
            model._state_cleaner = True
            setattr(Registry, 'setup_models', state_cleaner(model)(
                getattr(Registry, 'setup_models')))

    export_tmpl_id = fields.Many2one(
        'ir.model.export.template', 'Template', readonly=True, required=True,
        ondelete='cascade', index=True)
    log_ids = fields.One2many(
        'smile.log', 'res_id', 'Logs', readonly=True,
        domain=[('model_name', '=', 'ir.model.export')])
    offset = fields.Integer()
    record_ids = fields.Text(
        'Records', readonly=True, required=True, default='[]')
    record_count = fields.Integer('# Records')

    def _execute(self):
        for rec in self:
            if not rec.record_ids:
                raise UserError(
                    _("You cannot regenerate this export "
                      "because records to export didn't store"))
            record_ids = safe_eval(rec.record_ids)
            if record_ids or rec.export_tmpl_id.force_execute_action:
                records = rec.env[rec.export_tmpl_id.model_id.model].browse(
                    record_ids)
                if rec.export_tmpl_id.method:
                    if rec._context.get('original_cr'):
                        new_env = rec.env(cr=rec._context['original_cr'])
                        records = records.with_env(new_env)
                    args = safe_eval(rec.args or '[]')
                    kwargs = safe_eval(rec.export_tmpl_id.method_args or '{}')
                    return getattr(records, rec.export_tmpl_id.method)(
                        *args, **kwargs)
