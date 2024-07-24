from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class ShopGun(models.Model):
    _name = 'shop.gun'

    shop_name = fields.Char()
    owner_id = fields.Many2one('res.partner', string="Owner")
    onwer_name = fields.Char(related='owner_id.display_name', string="Owner shop")
    address_owner = fields.Char(related='owner_id.contact_address', string="Owner Address")
    address = fields.Char(string="Shop Address")
