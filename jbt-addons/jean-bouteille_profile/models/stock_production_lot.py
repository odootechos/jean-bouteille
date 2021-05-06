# -*- coding: utf-8 -*-
# Copyright 2020 subteno
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    manufacture_date = fields.Datetime(
        string='Manufacture Date'
    )
    ddm_date = fields.Datetime(
        string='DDM'
    )
    hd_number = fields.Float(
        string='HD Number'
    )

    _sql_constraints = [('name_ref_uniq', 'check(1=1)', 'No error'),]