# Copyright 2019-2020 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "tier.validation"]
    _state_from = ["draft", "sent", "to approve"]
    _state_to = ["purchase","approved"]

    _tier_validation_manual_config = False

    @api.model
    def _get_under_validation_exceptions(self):
        res = super(PurchaseOrder, self)._get_under_validation_exceptions()
        res.append("route_id")
        return res
