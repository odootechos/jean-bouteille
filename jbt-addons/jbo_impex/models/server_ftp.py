# -*- coding: utf-8 -*-

from odoo import models, api


class ServerFTP(models.Model):
    _inherit = 'server.ftp'

    @api.model
    def retrieve_all_files(self):
        """
        retrieve data in memory
        :return:
        """
        stock_picking_obj = self.env['stock.picking']
        model_import_obj = self.env['ir.model.import.template']
        template = model_import_obj.browse(self._context.get('template'))
        logger = self._context.get('logger')
        self.ensure_one()
        ftp = self.connect()
        data_summary = []
        files = ftp.nlst(self.filename)
        for file in files:
            datas = []
            ftp.retrbinary('RETR ' + file, lambda block: datas.append(block))
            data_summary.append((file, b''.join(datas).decode('utf-8')))
        ftp.close()
        return stock_picking_obj.processing_import_data(data_summary, template, logger)
