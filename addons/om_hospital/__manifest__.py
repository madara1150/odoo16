# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hospital Management',
    'version': '1.0',
    'category': 'Productivity',
    'sequence': -100,
    'summary': 'Hostpital Management Software',
    'description': """Hostpital Management Software""",
    'website': 'https://www.odoo.com',
    'depends': ['sale', 'mail'],
    'installable': True,
    'data': [
       'security/ir.model.access.csv',
       'data/data.xml',
       'wizard/create_appointment_view.xml',
       'wizard/search_appointment_view.xml',
       'views/patient_view.xml',
       'views/doctor_view.xml',
       'views/kids_view.xml',
       'views/appointment_view.xml',
       'views/patient_gender_view.xml',
       'views/sale.xml',
    ],
    'license': 'LGPL-3',
    'application': True,
    'auto_install': False,
    'installable': True
}
