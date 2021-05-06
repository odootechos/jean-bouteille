# -*- encoding: utf-8 -*-

from odoo import models, fields


class IrModelImportTemplate(models.Model):
    _inherit = 'ir.model.import.template'

    import_file = fields.Binary('File', attachment=True)
    file_name = fields.Char('Filename')
    export_xls = fields.Boolean('Generate errors file')
    attachment_ids = fields.Many2many('ir.attachment', 'model_import_template_attachment_rel', 'template_id',
                                      'attachment_id', 'Documents', readonly=True)
    is_remote_import = fields.Boolean(string='Use FTP')
    server_ftp_id = fields.Many2one("server.ftp", string="Choose FTP Server")

    def button_clean_history(self):
        self.ensure_one()
        self.attachment_ids.unlink()
        return True

