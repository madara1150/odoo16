{
    'name': 'Shop gun',
    'version': '16.0.0',
    'summary': 'sell the gun',
    'sequence': 5,
    'description': "Hello",
    'website': 'http://www.google.com',
    'category': 'Test',
    'author' : 'Madara Uchiha',
    'depends': ['base','resource','base_setup','mail'],
    'data': [
        'views/base_menu.xml',
        'views/shop_gun_view.xml',
        'views/customer_view.xml',
        'security/ir.model.access.csv',
        
    ],
    'assets': {
        
    },
    'application': True,
    'license': 'LGPL-3',
}