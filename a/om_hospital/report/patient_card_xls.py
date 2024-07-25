from odoo import api,fields, models

class PartnerCardXlsx(models.AbstractModel):
    _name = 'report.om_hospital.report_patient_id_card_xls'
    _inherit = 'report.report_xlsx.abstract'

def generate_xlsx_report(self, workbook, data, partners):
        for obj in partners:
            report_name = obj.name
            sheet = workbook.add_worksheet(report_name[:31])
            bold = workbook.add_format({'bold': True})
            sheet.write(0, 0, obj.name, bold)