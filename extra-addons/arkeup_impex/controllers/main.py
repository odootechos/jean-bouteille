# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2018 ArkeUp (<http://www.arkeup.fr>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import xlrd
import logging as logger
from io import BytesIO
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition, serialize_exception
from odoo.addons.arkeup_impex.lib.xlutils.copy import copy


class ExportAccount(http.Controller):
    @http.route('/export-impex', type='http', auth='user')
    def export_impex(self, id, **kw):
        try:
            export_id = request.env['ir.model.export.template'].browse(int(id))
            extension = export_id.filename.split('.')[-1]
            if extension in ['xls', 'xlsx']:
                workbook = copy(xlrd.open_workbook(export_id.path + export_id.filename, formatting_info=True))
                fp = BytesIO()
                workbook.save(fp)
                fp.seek(0)
                file_out = fp.read()
                fp.close()
            else:
                file_open = open(export_id.path + export_id.filename, 'r')
                file_out = file_open.read()
                file_open.close()
            xlsheader = [('Content-Type', 'application/octet-stream'),
                         ('Content-Disposition', content_disposition(export_id.filename))]
            return request.make_response(file_out, xlsheader)

        except Exception as error:
            logger.error(repr(error))
