# -*- coding: utf-8 -*-
# Copyright 2020 subteno
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from ftplib import FTP
from tempfile import NamedTemporaryFile
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError


import logging

_logger = logging.getLogger(__name__)


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    edi_id = fields.Many2one(
        string='EDI File',
        comodel_name='export.edi.file',
    )

    @api.model
    def _cron_generate_snapshots(self):
        _logger.info('>>>>>>>>>>>>>>>< processing the inventory stock snapshot start .......')
        self.generate_periodically_snapshots()
        _logger.info('>>>>>>>>>>>>> end of the process of snapshoting')

    @api.model
    def getList(self, dict):
        list = []
        for key in dict.keys():
            list.append(key)
        return list

    @api.model
    def generate_periodically_snapshots(self):
        host = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.url")
        login = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.login")
        passwd = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.password")
        port = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.port")
        if not login:
            raise UserError(_('Login is not configured'))
        ftp = FTP()
        ftp.connect(host, int(port))
        ftp.login(login, passwd)
        ftp.set_pasv(True)
        files = ftp.nlst()
        company = self.env['res.company'].search(
            [
                ('is_using_edi', '=', True)
            ], limit=1)
        if not company:
            raise UserError(_('NO CONFIGURATION FM was found'))
        company_id = company.id
        location = company.location_fm_id
        if not location:
            raise UserError(_('Please, Verify Configuration of Location FM'))
        location_id = location.id
        _logger.info('>>>>>>>>>>>>>>>>> There is all the files gotted from FM %s' % files)
        if len(files) > 0:
            for file in files:
                _logger.info('>>>>>>>>>>>>>>>>>>>>> start loop files ')
                if 'JBO_MAN_stk_' in file:
                    _logger.info('>>>>>>>>>>>>>>>>>>>>>>> Processing file %s ' % file)
                    today = datetime.today()
                    # Cancel the previous not CONFIRMED Adjustment
                    previous_name = 'FM ' + datetime.strftime(today - timedelta(1), '%d/%m/%Y')
                    inventory_ids = self.env['stock.inventory'].search(
                        [
                            ('name', '=', previous_name),
                            ('state', 'in', ['draft', 'confirm'])
                        ]
                    )
                    if inventory_ids:
                        for inventory in inventory_ids:
                            inventory.write(
                                {
                                    'state': 'cancel'
                                }
                            )
                    _logger.info('>>>>>>>>>>>>>>>>>>>>> Check if there is already FM inventory stock %s ' % inventory_ids)
                    name = 'FM ' + today.strftime('%d/%m/%Y')
                    inventory_id = self.env['stock.inventory'].search(
                        [
                            ('name', '=', name),
                            ('state', 'in', ['draft', 'confirm'])
                        ], limit=1)
                    stocks = {}
                    if not inventory_id:
                        inventory_id = self.env['stock.inventory'].create(
                            {
                                'name': name,
                                'date': datetime.now(),
                                'location_id': location_id,
                                'company_id': company_id,
                                'filter': 'partial',
                                'state': 'confirm',
                            }
                        )
                    else:
                        inventory_id.line_ids.unlink()
                    _logger.info('>>>>>>>>>>>>>>>>>>>< check if there is inventory with date of now %s' % inventory_id)
                    FMStockKQuant = self.env['stock.quant'].search([
                        ('company_id', '=', company_id),
                        ('location_id', '=', location_id),
                    ])
                    for quant in FMStockKQuant:
                        key = (quant.product_id, quant.lot_id)
                        stocks[key] = {
                            'product_id': quant.product_id.id,
                            'product_qty': 0,
                            'theoretical_qty': quant.quantity,
                            'company_id': company_id,
                            'location_id': location_id,
                            'prod_lot_id': quant.lot_id.id,
                        }
                    filename_dowload = NamedTemporaryFile(delete=False)
                    ftp.retrbinary('RETR %s' % file, filename_dowload.write)
                    filename_dowload.seek(0, 0)
                    lines = filename_dowload.readlines()
                    no_batch = self.env['stock.production.lot']
                    _logger.info('>>>>>>>>>>>>>>>>>>> Lines of file %s ' % lines)
                    for line in lines:
                        _logger.info('>>>>>>>>>>>>>>>>><< start processing line %s ' % line)
                        row = tuple(line.decode('ascii', 'ignore').split(';'))
                        if row:
                            _logger.info('>>>>>>>>>>>>>>>> OK there is row %s ' % str(row))
                            if row[2]:
                                product_id = self.env['product.product'].search(
                                    [
                                        ('default_code', '=', str(row[2]))
                                    ], limit=1)
                                if not product_id:
                                    raise ValidationError(_('Product Reference {code} is not Found').format(
                                        code=str(row[2])))
                                if row[12]:
                                    product_qty = row[12]
                                # Check if batch of product does exist
                                _logger.info('>>>>>>>>>>>>>>>>>>>>>>>> Product found %s' % str(product_id))
                                batch_number = row[4]
                                batch = no_batch
                                if batch_number:
                                    batch = self.env['stock.production.lot'].search(
                                        [
                                            ('name', '=', str(batch_number))
                                         ], limit=1)
                                    if not batch:
                                        batch = self.env['stock.production.lot'].create(
                                            {
                                                'name': str(batch_number),
                                                'product_id': product_id.id,
                                            }
                                        )
                                key = (product_id, batch)
                                if key in stocks:
                                    stocks[key].update(
                                        {
                                            'product_qty': product_qty
                                        }
                                    )
                                else:
                                    stocks[key] = {
                                        'product_id': product_id.id,
                                        'product_qty': product_qty,
                                        'theoretical_qty': 0,
                                        'company_id': company_id,
                                        'location_id': location_id,
                                        'prod_lot_id': batch.id,
                                    }
                    _logger.info('>>>>>>>>>>>>>>>>> is stock defined %s' % str(stocks))
                    if stocks:
                        lines = []
                        for key in stocks:
                            lines.append((0, 0, stocks[key]))
                            _logger.info('>>>>>>>>>>>>>< append line %s into %s ' % (stocks[key], str(lines)))
                        inventory_id.line_ids = lines
                    _logger.info('>>>>>>>>>>>>>>>>>>> OK there is all lines %s' % str(inventory_id.line_ids))
