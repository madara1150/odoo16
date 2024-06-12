from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class ShopGun(models.Model):
    _name = 'shop.gun'
    _description = 'shop sell gun'

    name = fields.Char(required=1, size=50)
    description = fields.Text()
    selling_price = fields.Float()
    state = fields.Selection([
        ('pre','Pre_Order'),
        ('selling','Selling'),
        ('reserved','Reserved'),
        ('sold','Sold_Out'),
    ], default='selling')
    customer_address = fields.Char()
    order_date = fields.Datetime(default=fields.Datetime.now())
    owner_id = fields.Many2one('owner')
    tag_ids = fields.Many2many('tag')