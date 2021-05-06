# -*- coding: utf-8 -*-
# from odoo import http


# class ArkeupImpex(http.Controller):
#     @http.route('/arkeup_impex/arkeup_impex/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/arkeup_impex/arkeup_impex/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('arkeup_impex.listing', {
#             'root': '/arkeup_impex/arkeup_impex',
#             'objects': http.request.env['arkeup_impex.arkeup_impex'].search([]),
#         })

#     @http.route('/arkeup_impex/arkeup_impex/objects/<model("arkeup_impex.arkeup_impex"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('arkeup_impex.object', {
#             'object': obj
#         })
