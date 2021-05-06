# -*- coding: utf-8 -*-

{
    'name': 'ArkeUp FTP Connector',
    'version': '1.0',
    'category': 'Tools',
    'sequence': -50,
    'summary': 'Manage FTP Connection',
    'author': 'Arkeup',
    'website': 'https://arkeup.com',
    'description': """
Manage FTP Connection 
=====================
- Connect to FTP from Odoo    
- Download files
- Upload files
""",
    'depends': ['base'],
    'data': [
        # data
        'data/ir_sequence.xml',
        # security
        'security/ir.model.access.csv',
        # views
        'views/server_ftp_view.xml',
    ],
    'license': 'AGPL-3',
    'qweb': [],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
