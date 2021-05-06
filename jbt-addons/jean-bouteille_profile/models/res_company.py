# -*- coding: utf-8 -*-
# Copyright 2020 Subteno IT
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    is_using_edi = fields.Boolean(
        string='Is using EDI FM'
    )
    location_fm_id = fields.Many2one(
        string='Location FM',
        comodel_name='stock.location',
    )
