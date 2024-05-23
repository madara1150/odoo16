from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    # สืบทอดสิ่งที่มีอยู่แล้ว
    _inherit = 'sale.order'

    # เพิ่ม field
    property_id = fields.Many2one('property')

    #ฟังก์ชั่นส่งฟอร์มของ sale ดึงมาดัดแปลงเพิ่มเติมจากเดิม
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        print("inside action_confirm method")
        return res




    