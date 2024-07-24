from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Customer(models.Model):
    _name = 'customer'

    name = fields.Char(required=1)
    phone = fields.Char()
    address = fields.Char()
    # shop_gun_ids = fields.One2many('shop.gun','owner_id')



    