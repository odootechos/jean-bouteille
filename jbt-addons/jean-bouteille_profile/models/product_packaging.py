# -*- coding: utf-8 -*-
# Copyright 2020 subteno
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    is_pallet = fields.Boolean(
        string='IS PALLET'
    )
    gross_weight = fields.Float(
        string='Gross Weight'
    )
    net_weight = fields.Float(
        string='Net Weight'
    )
    depth = fields.Float(
        string='Depth'
    )
    number_of_layer = fields.Float(
        string='Number of layer'
    )
    layer_height = fields.Float(
        string='Layer Height'
    )
