# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.models.chart_template import update_taxes_from_templates

def migrate(cr, version):
    # For April 5 Withholding Tax Code Updates
    update_taxes_from_templates(cr, 'l10n_ec.l10n_ec_ifrs')
