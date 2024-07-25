from odoo import api, fields, models, tools
# from odoo.addons.sale.models.sale import SaleOrder as OdooSaleOrder

class SaleOrder(models.Model):
    _inherit = "sale.order"

    sale_description = fields.Char(string='Sale Description')


    # def unlink(self):
    #     print("wdadadada")
    #     return super(OdooSaleOrder,self).unlink()