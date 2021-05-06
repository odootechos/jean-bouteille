# -*- coding: utf-8 -*-

from odoo import registry, fields, models, api, _
from datetime import datetime
import csv
import io
import base64


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def schedule_delivery_reception_process(self, **kwargs):
        with api.Environment.manage():
            with registry(self._cr.dbname).cursor() as new_cr:
                self = self.with_env(self.env(cr=new_cr))
                logger = self._context['logger']
                model_import_obj = self.env['ir.model.import.template']
                try:
                    template = model_import_obj.browse(kwargs.get('template_id'))
                    if template.is_remote_import:
                        if not template.server_ftp_id:
                            logger.info(_('No FTP server found. Please fill ftp server field to continue!'))
                            return False
                        return template.server_ftp_id.with_context(template=template.id, logger=logger).retrieve_all_files()
                    elif template.import_file:
                        content = [(template.file_name, base64.decodebytes(template.import_file).decode('utf-8-sig'))]
                        return self.processing_import_data(content, template, logger)
                except Exception as e:
                    logger.error(repr(e))
                    self._cr.rollback()

    def processing_import_data(self, datas=False, template=False, logger=False):
        """
        Method to process datas
        :param datas:
        :param template:
        :param logger:
        :return:
        """
        if not datas:
            logger.info(_('No files were retrieved from the FTP server.'))
            return False

        company = self.env['res.company'].search([('is_using_edi', '=', True)], limit=1)
        if not company:
            logger.info(_('Configuration Error : NO CONFIGURATION FM was found'))
            return False
        location = company.location_fm_id
        if not location:
            logger.info(_('Configuration Error : Please, Verify Configuration of Location FM'))
            return False

        location_id = location.id
        StockProductionLot = self.env['stock.production.lot']
        StockMoveLine = self.env['stock.move.line']

        errors = []

        for filename, data in datas:
            try:
                self._cr.commit()
                logger.info(_('Start processing file %s') % filename)
                csvfile = io.StringIO(data)
                reader = csv.reader(csvfile, delimiter=';')
                if 'JBO_MAN_cap_' in filename:

                    pickings_in = self.env['stock.picking']
                    lines_incoming = reader
                    check_move = True
                    for row in lines_incoming:

                        pick_name_ = row[0]
                        default_code_ = row[8]
                        delivery_carrier_name = row[5]
                        confirmation_date_ = row[6]
                        qty_done_ = row[15]
                        manufacture_date_ = row[12]
                        ddm_ = row[13]
                        batch_name = row[11]
                        product_qty_ = row[14]

                        check_delivery = True
                        picking_in = self.env['stock.picking'].search([('name', '=', pick_name_),
                                                                       ('location_dest_id.barcode', '=', 'FMM-STOCK'),
                                                                       ('state', 'not in', ['done', 'cancel'])])
                        if picking_in:
                            move_id = picking_in.mapped('move_lines').filtered(
                                lambda r: r.product_id.default_code == default_code_)
                            if len(move_id) == 0:
                                check_move = False
                            else:
                                carrier_id = self.env['delivery.carrier'].search([
                                    ('name', '=', delivery_carrier_name)])
                                if confirmation_date_:
                                    confirmation_date = datetime.strptime(confirmation_date_, '%Y%m%d%H%M%S')
                                if move_id.move_line_ids and len(move_id.move_line_ids) == 1 and move_id.product_id.tracking == 'none':
                                    move_id.move_line_ids.write({'qty_done': move_id.move_line_ids.qty_done + float(qty_done_)})
                                else:
                                    manufacture_date = False
                                    if manufacture_date_:
                                        manufacture_date = datetime.strptime(manufacture_date_, '%Y%m%d')
                                    ddm = False
                                    if ddm_:
                                        ddm = datetime.strptime(ddm_, '%Y%m%d')
                                    batch_id = StockProductionLot.search(
                                        [('name', '=', batch_name),
                                         ('product_id', '=', move_id.product_id.id)])
                                    if move_id.product_id.tracking == 'lot':
                                        if not batch_id:
                                            batch = StockProductionLot.search([
                                                ('name', '=', batch_name)])
                                            if batch:
                                                check_delivery = False
                                            batch_vals = {'name': batch_name, 'product_id': move_id.product_id.id,
                                                          'product_qty': float(product_qty_), 'manufacture_date': manufacture_date,
                                                          'use_date': ddm, }
                                            if check_delivery:
                                                batch_id = StockProductionLot.create(batch_vals)
                                    if qty_done_ != product_qty_:
                                        vals = {'move_id': move_id.id, 'product_id': move_id.product_id.id,
                                                'product_uom_id': move_id.product_uom.id, 'location_id': picking_in.location_id.id,
                                                'location_dest_id': picking_in.location_dest_id.id, 'picking_id': picking_in.id,
                                                'lot_id': batch_id.id, 'product_uom_qty': float(product_qty_)}
                                        if check_delivery:
                                            line = StockMoveLine.create(vals)
                                            line.write({'qty_done': line.qty_done + float(qty_done_)})
                                    elif qty_done_ == product_qty_ and \
                                            move_id.product_id.tracking != 'none' and len(move_id.move_line_ids) == 1:
                                        if check_delivery:
                                            move_id.move_line_ids.write({
                                                'qty_done': move_id.move_line_ids.qty_done + float(qty_done_),
                                                'lot_id': batch_id.id or False,
                                            })
                                if carrier_id and check_delivery:
                                    picking_in.write({
                                        'carrier_id': carrier_id.id,
                                        'date_done': confirmation_date})
                                pickings_in |= picking_in
                        else:
                            errors.append((filename, data))
                            logger.error(_('Thers is an error with this picking IN %s') % pick_name_)
                            self._cr.rollback()
                            break
                    if pickings_in and check_delivery and check_move:
                        pickings_in.action_done()
                elif 'JBO_MAN_sli_' in filename:
                    pickings_out = self.env['stock.picking']
                    lines_outgoing = reader
                    check_delivery = True
                    for row in lines_outgoing:
                        pick_name_ = row[0]
                        default_code_ = row[8]
                        carrier_ = row[5]
                        manufacture_date_ = row[12]
                        use_date_ = row[13]
                        confirmation_date_ = row[4]
                        qty_done_ = row[15]
                        batch_name = row[11]
                        carrier_tracking_ref = row[16]
                        weight = row[17]
                        check_delivery = True
                        picking_out = self.env['stock.picking'].search([('name', '=', pick_name_), ('location_id', '=', location_id),
                                                                        ('state', 'not in', ['done', 'cancel'])])
                        if picking_out:
                            picking_out.action_assign()
                            move_id = picking_out.mapped('move_lines').filtered(lambda r: r.product_id.default_code == default_code_)
                            carrier_id = self.env['delivery.carrier'].search([('name', '=', carrier_)])
                            confirmation_date = datetime.now()
                            manufacture_date = False
                            use_date = False
                            if manufacture_date_:
                                manufacture_date = datetime.strptime(manufacture_date_, '%Y%m%d')
                            if use_date_:
                                use_date = datetime.strptime(use_date_, '%Y%m%d')
                            if confirmation_date_:
                                confirmation_date = datetime.strptime(confirmation_date_, '%Y%m%d%H%M%S')
                            if move_id and len(move_id.move_line_ids) == 1 and move_id.product_id.tracking == 'none':
                                qty_done = move_id.move_line_ids.qty_done + float(qty_done_)
                                move_id.move_line_ids.write({'qty_done': qty_done, })
                            else:
                                batch_id = StockProductionLot.search([('name', '=', batch_name),
                                                                      ('product_id', '=', move_id.product_id.id)])
                                if not batch_id:
                                    batch = StockProductionLot.search([('name', '=', batch_name)], limit=1)
                                    if batch:
                                        check_delivery = False
                                    batch_vals = {'name': batch_name, 'product_id': move_id.product_id.id,
                                                  'product_qty': float(qty_done_), 'manufacture_date': manufacture_date,
                                                  'use_date': use_date}
                                    if check_delivery:
                                        batch_id = StockProductionLot.create(batch_vals)
                                lot_id = batch_id.id
                                if float(qty_done_) > move_id.product_uom_qty:
                                    if not move_id.move_line_ids:
                                        product_uom_id = move_id.product_uom.id
                                        move_id.write({'move_line_ids': [(0, 0, {'move_id': move_id.id, 'picking_id': picking_out.id,
                                                                                 'product_id': move_id.product_id.id,
                                                                                 'location_id': move_id.location_id.id,
                                                                                 'location_dest_id': move_id.location_dest_id.id,
                                                                                 'product_uom_id': product_uom_id,
                                                                                 'qty_done': float(qty_done_),
                                                                                 'lot_id': lot_id})]})
                                    if move_id.move_line_ids and move_id.move_line_ids[0].qty_done == 0:
                                        if check_delivery:
                                            move_id.move_line_ids[0].write({'qty_done': float(qty_done_),
                                                                            'lot_id': lot_id})
                                    else:
                                        vals = {'move_id': move_id.id, 'product_id': move_id.product_id.id,
                                                'product_uom_id': move_id.product_uom.id,
                                                'location_id': move_id.move_line_ids[0].location_id.id,
                                                'location_dest_id': move_id.move_line_ids[0].location_dest_id.id,
                                                'picking_id': picking_out.id, 'lot_id': batch_id.id}
                                        if check_delivery:
                                            line = self.env['stock.move.line'].create(vals)
                                            line.write({'qty_done': float(qty_done_)})
                                elif float(qty_done_) == move_id.product_uom_qty and move_id.product_id.tracking != 'none' and \
                                        len(move_id.move_line_ids) == 1:
                                    if check_delivery:
                                        move_id.move_line_ids.write({'qty_done': float(qty_done_), 'lot_id': batch_id.id})
                                else:
                                    move_id.write({'move_line_ids': [(0, 0, {'move_id': move_id.id, 'picking_id': picking_out.id,
                                                                             'product_id': move_id.product_id.id,
                                                                             'location_id': move_id.location_id.id,
                                                                             'location_dest_id': move_id.location_dest_id.id,
                                                                             'product_uom_id': move_id.product_uom.id,
                                                                             'qty_done': float(qty_done_), 'lot_id': lot_id})]})
                            if carrier_id and check_delivery:
                                picking_out.write({'carrier_id': carrier_id.id, 'carrier_tracking_ref': carrier_tracking_ref,
                                                   'weight': weight, 'date_done': confirmation_date})
                            pickings_out |= picking_out
                        else:
                            errors.append((filename, data))
                            logger.error(_('Thers is an error with this picking OUT %s') % pick_name_)
                            self._cr.rollback()
                            break
                    if pickings_out and check_delivery:
                        for picking in pickings_out:
                            picking.action_done()
                            order = self.env['sale.order'].search([('name', '=', picking.origin)], limit=1)
                            for pick in order.picking_ids:
                                state = 'not_Sent'
                                if pick.state == 'done':
                                    state = 'sent'
                                pick.write({'state_ftp': state})
            except Exception as e:
                logger.error(repr(e))
                self._cr.rollback()
                errors.append((filename, data))
        self.manage_import_report(template, errors, logger)

    @api.model
    def manage_import_report(self, template=False, errors=[], logger=None):
        """
        :param template:
        :param errors:
        :param logger:
        :return:
        """
        if not errors:
            self._cr.execute("""
                update error_history set error_occured=false where current_import_id={}
                """.format(template.id_current_import))
            self._cr.commit()
            return logger.info(_('Import done successfully.'))
        if template.export_xls:
            self.generate_errors_file(template, errors)
            self._cr.execute("""
                update error_history set error_occured=true where current_import_id={}
                """.format(template.id_current_import))
            self._cr.commit()
            logger.info(_('Import finish with errors. \n '
                                 'There is the liste of all stranded files : \n + %s \n'
                                 'Go to Histories tab to show the details.') % '\n + '.join([name for name, _ in errors]))
        return False

    @api.model
    def generate_errors_file(self, template=False, datas=[]):
        """
        Generate the file with all error lines
        :param template:
        :param data:
        :return:
        """
        if not datas or not template or not isinstance(datas, list):
            return False
        for file in datas:
            csv_data = io.StringIO()
            csv_writer = csv.writer(csv_data, delimiter=';')
            rows = [[row] for row in file[1].split('\n')]
            csv_writer.writerows(rows)
            content = base64.b64encode(csv_data.getvalue().encode('utf-8'))
            self.create_attachment(template, content, file[0])
        return True

    @api.model
    def create_attachment(self, template=False, content=None, filename=False):
        """
        Create error file in attachment
        :param template:
        :param content:
        :param filename:
        :return:²
        """
        if not template or not content:
            return False
        model = 'ir.model.import.template'
        template.attachment_ids = [(0, 0, {'type': 'binary', 'res_model': model, 'res_id': template.id, 'datas': content,
                                           'name': filename})]
        return True
