from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Building(models.Model):

    _name = 'building'
    _description = 'Building Record'
    _inherit = ['mail.thread','mail.activity.mixin']
    # ชื่อตรงข้างปุ่ม New ตอนนี้ตั้งค่าให้ใช้ ค่า code ในการแสดง ถ้าไม่ใส่จะใช้ name แทน  name = fields.Char()
    _rec_name = 'code'
    
    no = fields.Integer()
    code = fields.Char()
    description =  fields.Text()
    name = fields.Char()
    active = fields.Boolean(default=True)
