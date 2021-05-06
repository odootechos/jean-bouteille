{
    'name': "Custom partner",
    'version': "14.0",
    'author': "Sirius-Info",
    'summary': "Custom partner - Jean Bouteille",
    'description': "Custom partner - Jean Bouteille",
    'license':'LGPL-3',

    'data': [
        #===============#
        # Security File #
        #===============#

        'security/ir.model.access.csv',

        #===============#
        # Data views    #
        #===============#

        'views/partner_view.xml',

        #===============#
        # Data actions  #
        #===============#



        #===============#
        # Data menus    #
        #===============#

    ],

    'depends': ['base', 'sale'],
    'application': True,
}
