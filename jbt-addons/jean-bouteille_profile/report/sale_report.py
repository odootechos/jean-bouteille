from odoo import tools
from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    total_quantity = fields.Float(
        'Total Quantity (L)',
        readonly=True
    )

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['total_quantity'] = ", sum(l.product_uom_qty * 1 / u.factor) as total_quantity"
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
