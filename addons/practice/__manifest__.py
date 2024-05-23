{
    'name': 'Practice',
    'version': '1.0.0',
    'summary': 'มาเรียนกัน',
    'sequence': 5,
    'description': "Hello",
    'website': 'http://www.google.com',
    'category': 'Test',
    'author' : 'Madara',
    'depends': ['base', 'sale_management', 'mail'],
    'data': [
        'views/base_menu.xml',
        'views/property_view.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/owner_view.xml','views/tag_view.xml',
        'views/sale_order_view.xml',
        'views/building_view.xml',
        'reports/property_report.xml',
        'data/sequence.xml',
        'views/property_history_view.xml',
        'wizard/change_state_wizard_view.xml',
        
    ],
    'assets': {
        'web.assets_backend': ['practice/static/src/css/property.css'],
        'web.report_assets_common': ['practice/static/src/css/font.css']
    },
    'application': True,
}