# -*- coding: utf-8 -*-
# Copyright 2020 SUBTENO IT
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def write(self, vals):
        res = super(MrpProduction, self).write(vals)
        if vals.get("bom_id"):
            if self.move_raw_ids.filtered(lambda r: r.state == 'done'):
                raise UserError(_("You cannot change this BoM because movements have been posted."))
            self.action_cancel()
            self.move_raw_ids = None
            self.state = "confirmed"
            self._generate_moves()
        return res
