# -*- encoding: utf-8 -*-

{
    'name': 'ArkeUp IMPEX',
    'summary': 'Manage import / export file from interface using smile_impex',
    'description': '',
    'author': 'ArkeUp',
    'website': 'https://arkeup.com',
    'category': 'Tools',
    'version': '0.1',
    'sequence': -51,
    'depends': [
        'smile_impex',
        'arkeup_ftp'
    ],
    'data': [
        # views
        'views/ir_model_export_template_view.xml',
        'views/ir_model_import_template_view.xml',
    ],
}
