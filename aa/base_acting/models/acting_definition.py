from odoo import _, api, fields, models

class ActingDefinition(models.Model):
    _name = "acting.definition"
    _description = "acting Definition"
    
    @api.model
    def _get_default_name(self):
        return _("New Acting Validation")
    
    @api.model
    def _get_acting_model_names(self):
        res = []
        return res
    
    name = fields.Char(
        string="Description",
        required=True,
        default=lambda self: self._get_default_name(),
        translate=True,
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Referenced Model",
        domain=lambda self: [("model", "in", self._get_acting_model_names())],
    )
    model = fields.Char(related="model_id.model", index=True, store=True)