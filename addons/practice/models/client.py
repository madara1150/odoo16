from odoo import models, fields, api
from odoo.exceptions import ValidationError

# สืบทอด ทุกอย่างจะเหมือนกับ owner
class Client(models.Model):
    _name = 'client'
    _inherit = 'owner'




    