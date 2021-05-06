# -*- coding: utf-8 -*-
# Copyright 2020 subteno
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from tempfile import NamedTemporaryFile
from ftplib import FTP
from datetime import datetime
from odoo.exceptions import UserError
from ast import literal_eval

import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    edi_id = fields.Many2one(
        string='EDI File',
        comodel_name='export.edi.file',
    )
    state_ftp = fields.Selection([
        ('not_Sent', 'Not Sent'),
        ('sent', 'Sent'),
    ],
        string='State FTP',
        default='not_Sent',
    )
    flag = fields.Boolean(
        string='Flag',
        default=False
    )
    code = fields.Selection(
        [
            ('incoming', 'Vendors'),
            ('outgoing', 'Customers'),
            ('internal', 'Internal'),
            ('mrp_operation', 'Manufacturing Operation')
        ],
        string='Type of Operation',
        related='picking_type_id.code',
        store=True
    )

    def action_done(self):
        """Changes picking state to done by processing the Stock Moves of the Picking

        Normally that happens when the button "Done" is pressed on a Picking view.
        @return: True
        """
        todo_moves = self.mapped('move_lines').filtered(lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
        # Check if there are ops not linked to moves yet
        for pick in self:
            for ops in pick.move_line_ids.filtered(lambda x: not x.move_id):
                # Search move with this product
                moves = pick.move_lines.filtered(lambda x: x.product_id == ops.product_id)
                moves = sorted(moves, key=lambda m: m.quantity_done < m.product_qty, reverse=True)
                if moves:
                    ops.move_id = moves[0].id
                else:
                    new_move = self.env['stock.move'].create({
                                                    'name': _('New Move:') + ops.product_id.display_name,
                                                    'product_id': ops.product_id.id,
                                                    'product_uom_qty': ops.qty_done,
                                                    'product_uom': ops.product_uom_id.id,
                                                    'location_id': pick.location_id.id,
                                                    'location_dest_id': pick.location_dest_id.id,
                                                    'picking_id': pick.id,
                                                    'picking_type_id': pick.picking_type_id.id,
                                                   })
                    ops.move_id = new_move.id
                    new_move._action_confirm()
                    todo_moves |= new_move
                    #'qty_done': ops.qty_done})
        todo_moves._action_done()
        if not self.date_done:
            self.write({'date_done': fields.Datetime.now()})
        return True

    @api.model
    def _cron_inbound_confirmation(self):
        _logger.info('>>>>>>>>>>>>>>>>>>> cron called correctly')
        try:
            self.generate_confirmation_reception()
            _logger.info('>>>>>>>>>>>>>>>>>>>> end processing receptions/deliveries')
        except:
            pass

    @api.model
    def generate_confirmation_reception(self):
        _logger.info('>>>>>>>>>>>>>>>> start to confirm receptions/delevries .....')
        host = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.url")
        login = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.login")
        passwd = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.password")
        port = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.port")
        path = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.path")

        if not login:
            raise UserError(_('Login is not configured'))
        ftp = FTP()
        ftp.connect(host, int(port))
        ftp.login(login, passwd)
        ftp.set_pasv(True)
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
        StockProductionLot = self.env['stock.production.lot']
        StockMoveLine = self.env['stock.move.line']
        # IMPORT RECEPTION
        files = ftp.nlst(path)
        _logger.info('>>>>>>>>>>>>>>>>>>This is all files got : %s' % files)
        if len(files) > 0:
            for file in files:
                _logger.info('>>>>>>>>>>>>>>>processing file %s' % file)
                if 'JBO_MAN_cap_' in file:
                    _logger.info('>>>>>>>>>>> Is a reception ....')
                    pickings_in = self.env['stock.picking']
                    filename_reception_dowload = NamedTemporaryFile(delete=False)
                    ftp.retrbinary('RETR %s' % file, filename_reception_dowload.write)
                    filename_reception_dowload.seek(0, 0)
                    lines_incoming = filename_reception_dowload.readlines()
                    check_move = True
                    _logger.info('>>>>>>>>>>>>>>> lines incomming %s' % lines_incoming)
                    for line in lines_incoming:
                        row = tuple(line.decode('ascii', 'ignore').split(';'))
                        if row:
                            check_delivery = True
                            picking_in = self.env['stock.picking'].search(
                                [('name', '=', row[0]),
                                 ('location_dest_id.barcode', '=', 'FMM-STOCK'),
                                 ('state', 'not in', ['done','cancel'])])
                            if picking_in:
                                move_id = picking_in.mapped('move_lines').filtered(
                                    lambda r: r.product_id.default_code == row[8])
                                if len(move_id) == 0:
                                    check_move = False
                                else:
                                    carrier_id = self.env['delivery.carrier'].search([
                                        ('name', '=', row[5])])
                                    confirmation_date = datetime.now()
                                    if row[6]:
                                        confirmation_date = datetime.strptime(row[6], '%Y%m%d%H%M%S')
                                    if move_id and move_id.move_line_ids and len(
                                            move_id.move_line_ids) == 1 and \
                                            move_id.product_id.tracking == 'none':
                                        move_id.move_line_ids.write({
                                            'qty_done': move_id.move_line_ids.qty_done + float(row[15]),
                                        })
                                    else:
                                        manufacture_date = False
                                        if row[12]:
                                            manufacture_date = datetime.strptime(row[12], '%Y%m%d')
                                        ddm = False
                                        if row[13]:
                                            ddm = datetime.strptime(row[13], '%Y%m%d')
                                        batch_id = StockProductionLot.search(
                                            [('name', '=', row[11]),
                                             ('product_id', '=', move_id.product_id.id)])
                                        if move_id.product_id.tracking == 'lot':
                                            if not batch_id:
                                                batch = StockProductionLot.search([
                                                    ('name', '=', row[11])])
                                                if batch:
                                                    check_delivery = False
                                                batch_vals = {
                                                    'name': row[11],
                                                    'product_id': move_id.product_id.id,
                                                    'product_qty': float(row[14]),
                                                    'manufacture_date': manufacture_date,
                                                    'use_date': ddm,
                                                }
                                                if check_delivery:
                                                    batch_id = StockProductionLot.create(batch_vals)
                                        if row[15] != row[14]:
                                            vals = {
                                                'move_id': move_id.id,
                                                'product_id': move_id.product_id.id,
                                                'product_uom_id': move_id.product_uom.id,
                                                'location_id': picking_in.location_id.id,
                                                'location_dest_id': picking_in.location_dest_id.id,
                                                'picking_id': picking_in.id,
                                                'lot_id': batch_id.id or False,
                                                'product_uom_qty': float(row[14]),
                                            }
                                            if check_delivery:
                                                line = StockMoveLine.create(vals)
                                                line.write({'qty_done': line.qty_done + float(row[15])})
                                        elif row[15] == row[14] and \
                                                move_id.product_id.tracking != 'none' and len(move_id.move_line_ids) == 1:
                                            if check_delivery:
                                                move_id.move_line_ids.write({
                                                    'qty_done': move_id.move_line_ids.qty_done + float(row[15]),
                                                    'lot_id': batch_id.id or False,
                                                })
                                    if carrier_id and check_delivery:
                                        picking_in.write({
                                            'carrier_id': carrier_id.id,
                                            'date_done': confirmation_date})
                                    pickings_in |= picking_in
                    if len(pickings_in) > 0 and check_delivery and check_move:
                        for picking in pickings_in.ids:
                            self.env['stock.picking'].browse(picking).action_done()
                if 'JBO_MAN_sli_' in file:
                    # IMPORT DELIVERY
                    _logger.info('>>>>>>>>>>>>>>>>>>>>>>>Is a delivery %s ' % file)
                    pickings_out = self.env['stock.picking']
                    filename_delivery_dowload = NamedTemporaryFile(delete=False)
                    ftp.retrbinary('RETR %s' % file, filename_delivery_dowload.write)
                    filename_delivery_dowload.seek(0, 0)
                    lines_outgoing = filename_delivery_dowload.readlines()
                    check_delivery = True
                    _logger.info('>>>>>>>>>>>>>>>>>>< lines outgoing %s' % lines_outgoing)
                    for line in lines_outgoing:
                        row = tuple(line.decode('ascii', 'ignore').split(';'))
                        if row:
                            check_delivery = True
                            picking_out = self.env['stock.picking'].search(
                                [('name', '=', row[0]),
                                 ('location_id', '=', location_id),
                                 ('state', 'not in', ['done','cancel'])
                                 ])
                            _logger.info('>>>>>>>>>>>>>>>>> picking %s' % picking_out)
                            if picking_out:
                                _logger.info('>>>>>>>>>>>>>>>>>>>>>>>>> OK picking found %s' % picking_out.name)
                                picking_out.action_assign()
                                move_id = picking_out.mapped('move_lines').filtered(
                                    lambda r: r.product_id.default_code == row[8])

                                carrier_id = self.env['delivery.carrier'].search(
                                    [
                                        ('name', '=', row[5])
                                    ]
                                )
                                confirmation_date = datetime.now()
                                manufacture_date = False
                                use_date = False
                                if row[12]:
                                    manufacture_date = datetime.strptime(row[12], '%Y%m%d')
                                if row[13]:
                                    use_date = datetime.strptime(row[13], '%Y%m%d')
                                if row[4]:
                                    confirmation_date = datetime.strptime(row[4], '%Y%m%d%H%M%S')
                                if move_id and len(move_id.move_line_ids) == 1 and \
                                        move_id.product_id.tracking == 'none':
                                    qty_done = move_id.move_line_ids.qty_done + float(row[15])
                                    move_id.move_line_ids.write({
                                        'qty_done': qty_done,
                                    })
                                else:
                                    _logger.info('>>>>>>>>>>>>>>>>>>>>>><< manage lots ')
                                    batch_id = StockProductionLot.search([
                                        ('name', '=', row[11]),
                                        ('product_id', '=', move_id.product_id.id)])
                                    if not batch_id:
                                        batch = StockProductionLot.search([
                                            ('name', '=', row[11])])
                                        if batch:
                                            check_delivery = False
                                        batch_vals = {
                                            'name': row[11],
                                            'product_id': move_id.product_id.id,
                                            'product_qty': float(row[15]),
                                            'manufacture_date': manufacture_date,
                                            'use_date': use_date,
                                        }
                                        if check_delivery:
                                            batch_id = StockProductionLot.create(batch_vals)
                                    lot_id = batch_id.id
                                    if float(row[15]) > move_id.product_uom_qty:
                                        if len(move_id.move_line_ids) == 0:
                                            product_uom_id = move_id.product_uom.id
                                            move_id.write(
                                                {
                                                    'move_line_ids': [
                                                        (0, 0, {
                                                            'move_id': move_id.id,
                                                            'picking_id': picking_out.id,
                                                            'product_id': move_id.product_id.id,
                                                            'location_id': move_id.location_id.id,
                                                            'location_dest_id': move_id.location_dest_id.id,
                                                            'product_uom_id': product_uom_id,
                                                            'qty_done': float(row[15]),
                                                            'lot_id': lot_id,
                                                        })
                                                    ]
                                                }
                                            )
                                        if move_id.move_line_ids and move_id.move_line_ids[0].qty_done == 0:
                                            if check_delivery:
                                                move_id.move_line_ids[0].write(
                                                    {
                                                        'qty_done': float(row[15]),
                                                        'lot_id': lot_id,
                                                    }
                                                )
                                        else:
                                            vals = {
                                                'move_id': move_id.id,
                                                'product_id': move_id.product_id.id,
                                                'product_uom_id': move_id.product_uom.id,
                                                'location_id': move_id.move_line_ids[0].location_id.id,
                                                'location_dest_id': move_id.move_line_ids[0].location_dest_id.id,
                                                'picking_id': picking_out.id,
                                                'lot_id': batch_id.id,
                                            }
                                            if check_delivery:
                                                line = self.env['stock.move.line'].create(vals)
                                                line.write(
                                                    {
                                                        'qty_done': float(row[15]),
                                                    }
                                                )
                                    elif float(row[15]) == move_id.product_uom_qty and \
                                            move_id.product_id.tracking != 'none' and len(move_id.move_line_ids) == 1:
                                        if check_delivery:
                                            move_id.move_line_ids.write({
                                                'qty_done': float(row[15]),
                                                'lot_id': batch_id.id or False,
                                            })
                                    else:
                                        move_id.write(
                                            {
                                                'move_line_ids': [
                                                    (0, 0, {
                                                        'move_id': move_id.id,
                                                        'picking_id': picking_out.id,
                                                        'product_id': move_id.product_id.id,
                                                        'location_id': move_id.location_id.id,
                                                        'location_dest_id': move_id.location_dest_id.id,
                                                        'product_uom_id': move_id.product_uom.id,
                                                        'qty_done': float(row[15]),
                                                        'lot_id': lot_id,
                                                    })
                                                ]
                                            }
                                        )
                                if carrier_id and check_delivery:
                                    picking_out.write({
                                        'carrier_id': carrier_id.id,
                                        'carrier_tracking_ref': row[16],
                                        'weight': row[17],
                                        'date_done': confirmation_date
                                    })
                                pickings_out |= picking_out
                            else:
                                break
                    _logger.info('>>>>>>>>>>>>>>>> picking out %s and check delivery %s ' % (pickings_out, check_delivery))
                    if len(pickings_out) > 0 and check_delivery:
                        _logger.info('>>>>>>>>>>>>< ok i am in ')
                        for picking in pickings_out.ids:
                            _logger.info('>>>>>>>>>>>>>>>>< confirmation of %s ' % picking)
                            self.env['stock.picking'].browse(picking).action_done()
                            origin = self.env['stock.picking'].browse(picking).origin
                            order = self.env['sale.order'].search(
                                [
                                    ('name', '=', str(origin))
                                ], order="id desc"
                            )
                            _logger.info('----order.picking_ids.ids----')
                            if not order:
                                _logger.info('>>>>>>>>>>>>>>>>> There is no order found')
                                break
                            _logger.info(order[0].picking_ids.ids)
                            for element in order[0].picking_ids.ids:
                                _logger.info(element)
                                if self.env['stock.picking'].browse(element).state == 'done':
                                    self.env['stock.picking'].browse(element).write(
                                        {
                                            'state_ftp': 'sent'
                                        }
                                    )
                                else:
                                    self.env['stock.picking'].browse(element).write(
                                        {
                                            'state_ftp': 'not_Sent'
                                        }
                                    )


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    def _get_action(self, action_xmlid):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.display_name

        default_immediate_tranfer = True
        if self.env['ir.config_parameter'].sudo().get_param('stock.no_default_immediate_tranfer'):
            default_immediate_tranfer = False

        context = {
            'search_default_picking_type_id': [self.id],
            'default_picking_type_id': self.id,
            'default_immediate_transfer': default_immediate_tranfer,
            'default_company_id': self.company_id.id,
        }
        try:
            action_context = literal_eval(action['context'])
        except:
            action_context = literal_eval(str(context))
        context = {**action_context, **context}
        action['context'] = context
        return action