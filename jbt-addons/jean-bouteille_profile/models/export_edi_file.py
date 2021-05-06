# -*- coding: utf-8 -*-
# Copyright 2020 subteno
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, _, api
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import csv
from io import StringIO
from ftplib import FTP
import io
import base64


class ExportEdiItem(models.Model):
    _name = 'export.edi.file'
    _rec_name = 'filename'
    _description = 'Export Edi'

    @api.model
    def _type_default_get(self):
        export_type = 'item'
        context = self._context or {}
        if context.get('active_model') == 'stock.inventory':
            export_type = 'stock_snapshot'
        if context.get('active_id', False) and context.get('active_model') == 'stock.picking':
            picking_id = self.env['stock.picking'].search([('id', '=', int(self._context['active_id']))], limit=1)
            picking_type = picking_id.picking_type_id.code
            if picking_type == 'outgoing':
                export_type = 'preparation_order'
            if picking_type == 'incoming':
                export_type = 'inbound'
        return export_type

    @api.model
    def _model_default_get(self):
        active_model = ''
        context = self._context or {}
        if context.get('active_model'):
            active_model = context.get('active_model')
        return active_model

    export_file = fields.Binary(
        string='Export file',
        help='The export file.',)

    import_file = fields.Binary(
        string='Import file',
        help='The Imported file.',)
    import_filename = fields.Char(
        string='Import File Name'
    )
    filename = fields.Char(
        string='Name',
        size=64,
        help='Filename',
        default="edi_item.csv")
    edi_date = fields.Date(
        string='EDI Date'
    )
    export_type = fields.Selection(
        string='Export Type',
        selection=[
            ('item', 'Item'),
            ('inbound', 'Inbound'),
            ('preparation_order', 'Preparation Order '),
            ('stock_snapshot', 'Stock Snapshot')
        ],
        required=True,
        default=_type_default_get,
    )
    import_type = fields.Selection(
        string='Import Type',
        selection=[
            ('inbound_confirmation', 'Inbound confirmation'),
            ('despatch_confirmation', 'Despatch confirmation'),
        ],
        required=True,
        default='inbound_confirmation',
    )
    import_type = fields.Selection(
        string='Import Type',
        selection=[
            ('inbound_confirmation', 'Inbound confirmation'),
            ('despatch_confirmation', 'Despatch confirmation'),
            ('stock_snaphots', 'Stock Snapshots'),
        ],
        required=True,
        default='inbound_confirmation',
    )
    reexport = fields.Boolean(
        string='Reexport'
    )
    manage_batchs = fields.Boolean(
        string='Manage Batch'
    )
    active_picking = fields.Char(
        string='Active Picking'
    )
    active_model = fields.Char(
        string='Active Model',
        default=_model_default_get,
    )
    pickings = fields.Char(
        string='Picking'
    )
    not_found = fields.Text(
        string='Items Not Found',
        help='List of items which were not found during export.')
    check_not_found = fields.Boolean(
        string="Check if not exist",
        default=False
    )

    @api.onchange('export_type')
    def onchange_type_export(self):
        for line in self:
            current_type = line.export_type
            current_model = self._context.get('active_model')
            if current_model == 'product.template' and current_type != 'item':
                raise UserError(_('You are trying to export some entries that are not available for this model.'))
            if current_model == 'stock.picking' and current_type in ['item', 'stock_snapshot']:
                raise UserError(_('You are trying to export some entries that are not available for this model.'))
            if current_model == 'stock.inventory' and current_type != 'stock_snapshot':
                raise UserError(_('You are trying to export some entries that are not available for this model.'))

    def get_file(self):
        if self.import_type == 'inbound_confirmation':
            self.get_csv_inbound_confirmation()
        if self.import_type == 'despatch_confirmation':
            self.get_csv_despatch_confirmation()
        return True

    def get_file(self):
        if self.import_type == 'inbound_confirmation':
            self.get_csv_inbound_confirmation()
        if self.import_type == 'despatch_confirmation':
            self.get_csv_despatch_confirmation()
        return True

    def return_file(self):
        if self.export_type == 'item':
            if self.env.context.get('active_model') == 'product.template':
                products = self.env['product.template'].search([
                    ('id', 'in', self._context.get('active_ids'))
                ]).mapped('product_variant_ids')
            else:
                products = self.env['product.product'].search([
                    ('id', 'in', self._context.get('active_ids'))])
            self.generate_csv_items(products)
        if self.export_type == 'inbound':
            pickings_inbound = self.env['stock.picking'].search([
                ('id', 'in', self._context.get('active_ids'))])
            self.generate_csv_inbound(pickings_inbound)
        if self.export_type == 'preparation_order':
            preparation_orders = self.env['stock.picking'].search([
                ('id', 'in', self._context.get('active_ids'))])
            self.generate_csv_preparation_order(
                preparation_orders)
        if self.export_type == 'stock_snapshot':
            stock_snapshots = self.env['stock.inventory'].search([
                ('id', 'in', self._context.get('active_ids'))])
            self.generate_csv_stock_snapshots(
                stock_snapshots)
        view_id = self.env.ref('jean-bouteille_profile.view_export_edi_file').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Edi exported'),
            'res_model': 'export.edi.file',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'nodestroy': True,
        }

    def generate_csv_items(self, products):
        WINDOWS_LINE_ENDING = b'\r\n'
        UNIX_LINE_ENDING = b'\n'
        csv_file = StringIO()
        not_found = []
        csv_writer = csv.writer(csv_file, delimiter=';')
        product_exported_in_edi = products.filtered(lambda r: r.edi_id)
        if product_exported_in_edi and not self.reexport:
            raise ValidationError(
                _("There's products that are already exported, if you want to \
                    reexport them, please check Reexport"))
        for product in products:
            tracking = ''
            if product.tracking == 'lot':
                tracking = 1
            pallet = product.packaging_ids.filtered(lambda r: r.is_pallet)
            box = product.packaging_ids.filtered(lambda r: not r.is_pallet)
            if pallet:
                pallet = pallet[-1]
            if box:
                box = box[-1]
            if not product.default_code:
                not_found.append(
                    _("- The reference of the "
                      "product {name} is missing").format(name=product.name)
                )
            if pallet:
                if not box.qty:
                    not_found.append(
                        _("- The number of units in a pallet of the product {name} is missing"
                          "").format(name=product.name)
                    )
                if not pallet.qty:
                    not_found.append(
                        _("- The number of layer of the product {name} is missing").format(name=product.name)
                    )
                if not pallet.layer_height:
                    not_found.append(
                        _("- The layer height of the product {name} is missing").format(name=product.name)
                    )
            vals = [
                product.default_code or '',
                product.name or '',
                '',
                '',
                product.expiration_time or '',
                '',
                '',
                '',
                '',
                product.weight or '',
                product.gross_weight or '',
                product.height or '',
                product.width or '',
                product.depth or '',
                product.barcode or '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                int(box.qty) or '',
                box.net_weight or '',
                box.gross_weight or '',
                box.height or '',
                box.width or '',
                box.depth or '',
                box.barcode or '',
                pallet.qty or '',
                '',
                '',
                '',
                pallet.number_of_layer or '',
                pallet.layer_height or '',
                '',
                '',
                '',
                '',
                '',
                '',
                product.icpe_code or '',
                '',
                '',
                '',
                '',
                tracking or '',
                '',
            ]
            csv_writer.writerow(vals)
        if len(not_found) > 0:
            self.write({
                'not_found': '\n'.join(not_found), 'check_not_found': True
            })
            return self
        self.filename = datetime.now().strftime(
            '%Y-%m-%d_%H%M') + 'JBO_MAN_items.csv'
        windows_csv = csv_file.getvalue().encode()
        unix_csv = windows_csv.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)
        file = base64.encodestring(unix_csv)
        self.export_file = file
        self.edi_date = fields.date.today()
        products.write({'edi_id': self.id})
        return self

    def generate_csv_preparation_order(self, preparation_orders):
        WINDOWS_LINE_ENDING = b'\r\n'
        UNIX_LINE_ENDING = b'\n'
        pickings = ''
        not_found = []
        preparation_orders = preparation_orders.filtered(
            lambda r: r.state not in ('cancel', 'done', 'draft'))
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file, delimiter=';')
        preparation_orders_exported_in_edi = preparation_orders.filtered(
            lambda r: r.edi_id)
        if preparation_orders_exported_in_edi and not self.reexport:
            raise ValidationError(
                _("There's preparations orders that are already exported, if you want to \
                    reexport them, please check Reexport"))
        if preparation_orders.filtered(
                lambda r: r.picking_type_id.code != 'outgoing'):
            raise ValidationError(
                _("You have selected the wrong type of EDI"))
        for order in preparation_orders:
            if order.location_id.barcode == 'FMM-STOCK':
                pickings = pickings + order.name + ','
                if not order.partner_id.ref:
                    not_found.append(
                        _("- The reference of the partner {name} is missing").format(name=order.partner_id.name)
                    )
                if not order.partner_id.street:
                    not_found.append(
                       _("- The street in the address of the partner {name} is "
                         "missing").format(name=order.partner_id.name)
                    )
                if not order.partner_id.zip:
                    not_found.append(
                        _("- The zip code of the partner {name} is missing").format(name=order.partner_id.name)
                    )
                if not order.partner_id.city:
                    not_found.append(
                        _("- The city of the partner {name} is missing").format(name=order.partner_id.name)
                    )
                if not order.scheduled_date:
                    not_found.append(
                        _("- The delivery date of the picking {name} is missing").format(name=order.name)
                    )
                vals = [
                    order.name or '',
                    order.partner_id.ref or '',
                    order.partner_id.name or '',
                    order.partner_id.street or '',
                    order.partner_id.street2 or '',
                    order.partner_id.zip or '',
                    order.partner_id.city or '',
                    order.partner_id.country_id.code or '',
                    order.sale_id.client_order_ref or '',
                    order.scheduled_date.strftime('%Y%m%d') or '',
                    '',
                    '',
                    '',
                    '',
                    order.origin or '',
                    order.partner_id.comment or '',
                    '',
                ]
                for move in order.move_ids_without_package:
                    if move.move_line_ids:
                        qty_product = 0
                        for line in move.move_line_ids:
                            if line.product_id.id == move.product_id.id:
                                qty_product += line.product_uom_qty
                        line_row = [
                            move.product_id.default_code or '',
                            '',
                            '',
                            '',
                            '',
                            move.product_id.to_manufacture,
                            '',
                            int(qty_product) or 0,
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            order.carrier_id.name or '',
                            order.partner_id.phone or '',
                            order.partner_id.email or '',
                            '',
                        ]
                        row = vals + line_row
                        csv_writer.writerow(row)
                    else:
                        move_row = [
                            move.product_id.default_code or '',
                            '',
                            '',
                            '',
                            '',
                            move.product_id.to_manufacture or '',
                            '',
                            int(move.reserved_availability) or 0,
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            '',
                            order.carrier_id.name or '',
                            order.partner_id.phone or '',
                            order.partner_id.email or '',
                            '',
                        ]
                        row = vals + move_row
                        csv_writer.writerow(row)
            else:
                raise ValidationError(_("You have selected the wrong Location"))
        if len(not_found) > 0:
            self.write({
                'not_found': '\n'.join(not_found), 'check_not_found': True
            })
            return self
        self.filename = datetime.now().strftime(
            '%Y-%m-%d_%H%M') + '_JBO_MAN_preparation_orders.csv'
        windows_csv = csv_file.getvalue().encode()
        unix_csv = windows_csv.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)
        file = base64.encodestring(unix_csv)
        self.export_file = file
        self.pickings = pickings
        self.edi_date = fields.date.today()
        preparation_orders.write({'edi_id': self.id})
        return self

    def generate_csv_inbound(self, pickings_inbound):
        WINDOWS_LINE_ENDING = b'\r\n'
        UNIX_LINE_ENDING = b'\n'
        pickings = ''
        not_found = []
        pickings_inbound = pickings_inbound.filtered(
            lambda r: r.state not in ('cancel', 'done', 'draft'))
        csv_file = StringIO()
        csv_writer = csv.writer(csv_file, delimiter=';')
        pickings_inbound_exported_in_edi = pickings_inbound.filtered(
            lambda r: r.edi_id)
        if pickings_inbound_exported_in_edi and not self.reexport:
            raise ValidationError(
                _("There's picking inbounds that are already exported, if you want to \
                    reexport them, please check Reexport"))
        if pickings_inbound.filtered(
                lambda r: r.picking_type_id.code != 'incoming'):
            raise ValidationError(
                _("You have selected the wrong type of EDI"))
        for inbound in pickings_inbound:
            if inbound.location_dest_id.barcode == 'FMM-STOCK':
                pickings = pickings + inbound.name + ','
                if not inbound.partner_id.ref:
                    not_found.append(
                        _("- The code of the partner {name} is missing").format(name=inbound.partner_id.name)
                    )
                if not inbound.partner_id.street:
                    not_found.append(
                        _("- The street in the address of the partner {name} is missing"
                          "").format(name=inbound.partner_id.name)
                    )
                vals = [
                    inbound.name or '',
                    '',
                    '',
                    inbound.partner_id.ref or '',
                    inbound.partner_id.name or '',
                    inbound.partner_id.street or '',
                    inbound.partner_id.street2 or '',
                    inbound.partner_id.zip or '',
                    inbound.partner_id.city or '',
                    inbound.partner_id.country_id.code or '',
                    inbound.purchase_id.name or '',
                    inbound.carrier_id.name or '',
                    inbound.scheduled_date.strftime('%Y%m%d') or '',
                    inbound.note or '',
                    '',
                    '',
                ]
                for move in inbound.move_lines:
                    move_row = [
                        move.product_id.default_code or '',
                        '',
                        '',
                        '',
                        '',
                        int(move.product_uom_qty) or '',
                        '',
                    ]
                    row = vals + move_row
                    csv_writer.writerow(row)
            else:
                raise ValidationError(_("You have selected the wrong Location"))
        if len(not_found) > 0:
            self.write({
                'not_found': '\n'.join(not_found), 'check_not_found': True
            })
            return self
        self.filename = datetime.now().strftime(
            '%Y-%m-%d_%H%M') + '_JBO_MAN_inbound.csv'
        windows_csv = csv_file.getvalue().encode()
        unix_csv = windows_csv.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)
        file = base64.encodebytes(unix_csv)
        self.export_file = file
        self.edi_date = fields.date.today()
        self.pickings = pickings
        pickings_inbound.write({'edi_id': self.id})
        return self

    def get_csv_stock_snapshots(self):
        content = base64.b64decode(self.import_file).decode('utf-8', 'ignore')
        content = content.replace('\r', '\n')
        f = StringIO(content)
        Stockinventory = self.env['stock.inventory']
        reader = csv.reader(f, delimiter=';')
        company_id = self.env.user.company_id.id
        for row in reader:
            if row:
                filter = 'partial'
                product_qty = 0
                product_uom_id = False
                prod_lot_id = False
                date_adjustment = datetime.now()
                if row[0]:
                    adjustment_stock = self.env['stock.inventory'].search([('name', '=', str(row[0]))], limit=1)
                    if adjustment_stock:
                        raise ValidationError(_('Adjustment Stock already Exist'))
                if row[1]:
                    date_adjustment = datetime.strptime(row[1], '%Y%m%d%H%M%S')
                company_id = self.env['res.company'].search([('id', '=', company_id)], limit=1).id
                if row[2]:
                    product_id = self.env['product.product'].search([('default_code', '=', str(row[2]))], limit=1)
                else:
                    raise ValidationError(_('Reference Product is missing'))
                if product_id.uom_id:
                    product_uom_id = product_id.uom_id.id
                name_adjustment = row[0]
                if row[12]:
                    product_qty = row[12]
                location_id = self.env['stock.location'].search(
                    [('barcode', '=', 'FMM-STOCK'), ('company_id', '=', company_id)], limit=1).id
                if not location_id:
                    raise ValidationError(_('Emplacement non existant'))
                batch_number = row[4]
                if batch_number:
                    prod_lot_id = self.env['stock.production.lot'].create({
                        'name': str(batch_number),
                        'product_id': product_id.id,
                    })
                inventory_id = Stockinventory.search([('name', '=', name_adjustment)], limit=1)
                if inventory_id:
                    inventory_id.line_ids = [(0, 0, {
                        'product_id': product_id.id,
                        'product_qty': product_qty,
                        'company_id': company_id,
                        'location_id': location_id,
                        'inventory_id': inventory_id.id,
                        'prod_lot_id': prod_lot_id,
                    })]
                    inventory_id.line_ids.sudo()._onchange_quantity_context
                    inventory_id.sudo()._onchange_location_id
                    inventory_id.line_ids.theoretical_qty = product_id.qty_available
                else:
                    inventory_id = self.env['stock.inventory'].create({
                        'name': name_adjustment,
                        'date_adjustment': date_adjustment,
                        'company_id': company_id,
                        'filter': filter,
                        'state': 'confirm',
                    })
                    inventory_id.line_ids = [(0, 0, {
                        'product_id': product_id.id,
                        'product_qty': product_qty,
                        'company_id': company_id,
                        'location_id': location_id,
                        'inventory_id': inventory_id.id,
                        'prod_lot_id': prod_lot_id,
                    })]
                    inventory_id.line_ids.sudo()._onchange_quantity_context
                    inventory_id.sudo()._onchange_location_id
                    inventory_id.line_ids.theoretical_qty = product_id.qty_available

    def directory_exists(self, ftp, dir_="/"):
        filelist = []
        ftp.retrlines('LIST',filelist.append)
        for f in filelist:
            if f.split()[-1] == dir_:
                return True
        return False

    def send_via_ftp(self):
        now = datetime.now()
        date_string = now.strftime("%Y%m%d%H%M%S")
        host = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.url")
        login = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.login")
        passwd = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.password")
        port = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.port")
        path = self.env["ir.config_parameter"].sudo().get_param("edi.jean-bouteille.ftp.path")
        if not login:
            raise UserError(_('Login is not configured'))
        export_file = self.export_file
        if not export_file:
            raise UserError(_('File is not loaded'))
        file_name = ''
        binary_stream = io.BytesIO()
        try:
            if self.export_type == 'item':
                file_name = 'JBO_MAN_pdt_' + date_string + '.csv'
            if self.export_type == 'inbound':
                file_name = 'JBO_MAN_app_' + date_string + '.csv'
            if self.export_type == 'inbound_confirmation':
                file_name = 'JBO_MAN_cap_' + date_string + '.csv'
            if self.export_type == 'preparation_order':
                file_name = 'JBO_MAN_cde_' + date_string + '.csv'
            if self.export_type == 'despatch_confirmation':
                file_name = 'JBO_MAN_sli_' + date_string + '.csv'
            if self.export_type == 'stock_snapshot':
                file_name = 'JBO_MAN_stk_' + date_string + '.csv'
            binary_stream.write(base64.decodebytes(export_file))
            if self.pickings:
                for picking in self.pickings.split(","):
                    picking_id = self.env['stock.picking'].search([('name', '=', picking)], limit=1)
                    picking_id.write({'state_ftp': 'sent'})
            binary_stream.seek(0)
            ftp = FTP()
            ftp.connect(host, int(port))
            ftp.login(login, passwd)
            ftp.set_pasv(True)
            if not self.directory_exists(ftp,path):
                ftp.mkd(path)
            ftp.cwd(path)
            ftp.storbinary('STOR ' + file_name, binary_stream)
            ftp.retrlines('LIST')
        except:
            "failed to login"

    def get_csv_inbound_confirmation(self):
        content = base64.b64decode(self.import_file).decode('utf-8', 'ignore')
        content = content.replace('\r', '\n')
        f = StringIO(content)
        StockProductionLot = self.env['stock.production.lot']
        StockMoveLine = self.env['stock.move.line']
        reader = csv.reader(f, delimiter=';')
        pickings_in = self.env['stock.picking']
        for row in reader:
            if row:
                picking_in = self.env['stock.picking'].search(
                    [('name', '=', row[0]),
                     ('state', '!=', ('done', 'cancel'))])
                move_id = picking_in.mapped('move_lines').filtered(
                    lambda r: r.product_id.default_code == row[8])
                carrier_id = self.env['delivery.carrier'].search([
                    ('name', '=', row[5])])
                confirmation_date = datetime.strptime(row[6], '%Y%m%d%H%M%S')
                if move_id and move_id.move_line_ids and len(
                    move_id.move_line_ids) == 1 and \
                        move_id.product_id.tracking == 'none':
                    move_id.move_line_ids.write({
                        'qty_done': float(row[15])
                    })
                else:
                    manufacture_date = False
                    if row[12]:
                        manufacture_date = datetime.strptime(row[12], '%Y%m%d')
                    ddm = False
                    if row[13]:
                        ddm = datetime.strptime(row[13], '%Y%m%d')
                    batch_vals = {
                        'name': row[11],
                        'product_id': move_id.product_id.id,
                        'product_qty': float(row[15]),
                        'hd_number': row[16],
                        'manufacture_date':
                            manufacture_date,
                        'ddm_date':
                            ddm,
                    }
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
                            'product_uom_qty': (row[14]),
                        }
                        line = StockMoveLine.create(vals)
                        line.write({'qty_done': float(row[15])})
                    elif row[15] == row[14] and\
                            move_id.product_id.tracking != 'none' and len(move_id.move_line_ids) == 1:
                        move_id.move_line_ids.write({
                            'qty_done': float(row[15]),
                            'lot_id': batch_id.id or False,
                        })
                if carrier_id:
                    picking_in.write({
                        'carrier_id': carrier_id.id,
                        'date_done': confirmation_date})
                pickings_in |= picking_in
        pickings_in.action_done()

    def get_csv_despatch_confirmation(self):
        content = base64.b64decode(self.import_file).decode('utf-8', 'ignore')
        content = content.replace('\r', '\n')
        f = StringIO(content)
        StockProductionLot = self.env['stock.production.lot']
        StockMoveLine = self.env['stock.move.line']
        reader = csv.reader(f, delimiter=';')
        pickings_out = self.env['stock.picking']
        for row in reader:
            if row:
                picking_out = self.env['stock.picking'].search(
                    [('name', '=', row[0]),
                     ('state', '!=', ('done', 'cancel'))])
                move_id = picking_out.mapped('move_lines').filtered(
                    lambda r: r.product_id.default_code == row[8])
                carrier_id = self.env['delivery.carrier'].search([
                    ('name', '=', row[5])])
                confirmation_date = datetime.strptime(row[4], '%Y%m%d%H%M%S')
                if move_id and move_id.move_line_ids and len(
                    move_id.move_line_ids) == 1 and \
                        move_id.product_id.tracking == 'none':
                    move_id.move_line_ids.write({
                        'qty_done': float(row[15]),
                    })

                else:
                    batch_id = StockProductionLot.search([
                        ('name', '=', row[11])])
                    if not batch_id:
                        manufacture_date = False
                        if row[12]:
                            manufacture_date = datetime.strptime(
                                row[12], '%Y%m%d')
                        ddm = False
                        if row[13]:
                            ddm = datetime.strptime(row[13], '%Y%m%d')
                        batch_vals = {
                            'name': row[11],
                            'product_id': move_id.product_id.id,
                            'product_qty': float(row[15]),
                            'hd_number': row[16],
                            'manufacture_date':
                                manufacture_date,
                            'ddm_date':
                                ddm,
                        }
                        batch_id = StockProductionLot.create(batch_vals)
                    if row[15] != row[14]:
                        dest_loc_id = picking_out.location_dest_id.id
                        vals = {
                            'move_id': move_id.id,
                            'product_id': move_id.product_id.id,
                            'product_uom_id': move_id.product_uom.id,
                            'location_id': picking_out.location_id.id,
                            'location_dest_id': dest_loc_id,
                            'picking_id': picking_out.id,
                            'lot_id': batch_id.id or False,
                            'product_uom_qty': (row[14]),
                        }
                        line = StockMoveLine.create(vals)
                        line.write({'qty_done': float(row[15])})
                    elif row[15] == row[14] and\
                            move_id.product_id.tracking != 'none' and len(move_id.move_line_ids) == 1:
                        move_id.move_line_ids.write({
                            'qty_done': float(row[15]),
                            'lot_id': batch_id.id or False,
                        })
                if carrier_id:
                    picking_out.write({
                        'carrier_id': carrier_id.id,
                        'carrier_tracking_ref': row[16],
                        'weight': row[17],
                        'date_done': confirmation_date
                    })
                pickings_out |= picking_out
        pickings_out.action_done()
