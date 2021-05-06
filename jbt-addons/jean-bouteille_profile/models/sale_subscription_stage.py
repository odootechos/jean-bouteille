# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleSubscriptionStage(models.Model):
    _inherit = 'sale.subscription.stage'

    do_invoice = fields.Boolean(string='Do invoice', default=False)
