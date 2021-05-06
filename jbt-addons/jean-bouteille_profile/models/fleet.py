# -*- coding: utf-8 -*-
from odoo import models, api

class FleetVehicleLogContract(models.Model):
    _inherit = "fleet.vehicle.log.contract"

    @api.depends('vehicle_id.name', 'cost_subtype_id')
    def _compute_contract_name(self):
        for record in self:
            name = record.vehicle_id.name
            if name and record.cost_subtype_id.name:
                name = record.cost_subtype_id.name + ' ' + name
            record.name = name