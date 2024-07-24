# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Holiday Check',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': -100,
    'summary': 'test',
    'description': """Hostpital Management Software""",
    'website': 'https://www.odoo.com/hacker',
    'depends': ['hr', 'calendar', 'resource'],
    'installable': True,
    'data': [
       'views/ct_holiday_view.xml',
       'views/user_view.xml',
       'views/base_menu.xml',
    ],
    'license': 'LGPL-3',
    'application': True,
    'auto_install': False,
    'installable': True
}
