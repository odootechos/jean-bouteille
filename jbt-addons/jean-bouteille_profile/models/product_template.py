# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    old_products = fields.Boolean(string='Old product')
    so_unit = fields.Many2one(
        string='Sale unit',
        comodel_name='uom.uom',
        help='So Unit.',
    )
    product_purchase_unit = fields.Many2one(
        string='Purchase Unit',
        comodel_name='uom.uom',
        help='Purchase Unit',
    )
    icpe_code = fields.Integer(
        string='ICPE CODE'
    )
    gross_weight = fields.Float(
        string='Gross Weight'
    )
    height = fields.Float(
        string='Height in cm'
    )
    width = fields.Float(
        string='Width'
    )
    depth = fields.Float(
        string='Depth'
    )
    edi_id = fields.Many2one(
        string='EDI File',
        comodel_name='export.edi.file',
    )
    to_manufacture = fields.Selection(
        string='To Manufacture',
        selection=[
            ('0', 'To manufacture'),
            ('1', 'Do not manufacture'),
        ],
        default='0',
    )

    @api.onchange('uom_id', 'uom_po_id')
    def _onchange_filter_uom_on_product(self):
        for record in self:
            return {'domain':
                    {
                        'so_unit': [('category_id', '=', record.uom_id.category_id.id)],
                        'product_purchase_unit': [('category_id', '=', record.uom_po_id.category_id.id)]
                    }
                    }
