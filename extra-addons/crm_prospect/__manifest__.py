# coding: utf-8

# Author: Sirius-Info
{
    'name': "CRM Prospect by Sirius-Info",
    'version': "14.0",
    'author': "Sirius-Info",
    'summary': "Add a Prospect / Customer toggle in partner.",
    'description': "Add a Prospect / Customer toggle in partner. If a sale is confirm then the partner is automatically mark as a customer. Add a sequence for internal reference in partner",
    'license':'LGPL-3',

    'data': [
        #===============#
        # Security File #
        #===============#

        # 'security/ir.model.access.csv',

        #===============#
        # Data actions  #
        #===============#

        # 'datas/sample_data.xml',
        'data/partner_ref_ir_sequence.xml',

        #===============#
        # Data views    #
        #===============#

        # 'views/sample_view.xml',
        'views/partner_view.xml',

        #===============#
        # Data report   #
        #===============#

        # 'report/sample_new_report.xml',
        # 'report/sample_paperformat.xml',
        # 'report/sample_inherited_report.xml',
    ],

    'depends': [
        'base',
        'sale',
        'contacts',
        # 'project',
        # 'stock',
    ],
    'application': True,
}
