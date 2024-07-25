# Copyright 2019-2020 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models


class ActingDefinition(models.Model):
    _inherit = "acting.definition"

    @api.model
    def _get_acting_model_names(self):
        res = super(ActingDefinition, self)._get_acting_model_names()
        res.append("purchase.order")
        return res
