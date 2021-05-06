# -*- coding: utf-8 -*-
# from odoo import http


# class SaleTimesheet(http.Controller):
#     @http.route('/sale_timesheet/sale_timesheet/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_timesheet/sale_timesheet/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_timesheet.listing', {
#             'root': '/sale_timesheet/sale_timesheet',
#             'objects': http.request.env['sale_timesheet.sale_timesheet'].search([]),
#         })

#     @http.route('/sale_timesheet/sale_timesheet/objects/<model("sale_timesheet.sale_timesheet"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_timesheet.object', {
#             'object': obj
#         })
