# -*- coding: utf-8 -*-

{
    'name': 'JBO IMPEX',
    'summary': """Manage Jean Bouteille import files""",
    'description': """
        Manage Jean Bouteille import files using FTP with logs
    """,
    'author': 'ArkeUp',
    'website': 'https://arkeup.com',
    'version': '0.1',
    'category': 'Tools',
    'sequence': -99,
    'depends': ['arkeup_impex', 'jean-bouteille_profile'],
    'data': [
        # data
        'data/server_ftp_data.xml',
        'data/ir_model_import_template_data.xml',
        # security
        'security/ir.model.access.csv',
        # views
        'views/ir_model_import_template_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
