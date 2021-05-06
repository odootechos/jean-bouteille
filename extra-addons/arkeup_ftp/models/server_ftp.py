# -*- coding: utf-8 -*-

import io
import logging

from ftplib import FTP

from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError

_logger = logging.getLogger(__name__)

datas = []

class ServerFTP(models.Model):
    _name = 'server.ftp'
    _description = 'Server FTP'

    name = fields.Char(copy=False)
    url = fields.Char('URL', required=True)
    login = fields.Char('Login')
    password = fields.Char('Password')
    filename = fields.Char('Filename', default='/', required=True, help='Complete remote path of the file to be downloaded')
    active = fields.Boolean(default=True)
    port = fields.Integer('Port')

    @api.model
    def default_get(self, fields):
        res = super(ServerFTP, self).default_get(fields)
        if not res.get('name') and 'name' not in res:
            res.update({'name': self.env['ir.sequence'].next_by_code('server.ftp.seq')})
        return res

    def connect(self):
        self.ensure_one()
        _logger.info(_('starting ftp connection ...'))
        try:
            if self.port:
                ftp = FTP()
                ftp.connect(self.url, self.port)
            else:   
                ftp = FTP(self.url)
            ftp.set_pasv(True)
            ftp.login(self.login, self.password)
            _logger.info(_('connection established succesfully.'))
        except Exception as e:
            raise Warning(repr(e))
        return ftp

    def retrieve_data(self):
        """
        retrieve data in memory
        :return:
        """
        self.ensure_one()
        ftp = self.connect()
        datas = []
        ftp.retrbinary('RETR ' + self.filename, lambda block: datas.append(block))
        ftp.close()
        return b''.join(datas)

    def button_check_connection(self):
        """
        check if all parameters are correctly set
        :return:
        """
        ftp = self.connect()
        if ftp:
            title = _('Connection Test Succeeded!')
            message = _('Everything seems properly set up!')
            ftp.close()
            raise ValidationError('%s\n%s' % (title, message))

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals.update({'name': self.env['ir.sequence'].next_by_code('server.ftp.seq')})
        return super(ServerFTP, self).create(vals)

    def store_data(self, filename=False, writer=False):
        """
        send data to the FTP
        :param filename:
        :param content:
        :return:
        """
        self.ensure_one()
        ftp = self.connect()
        writer.seek(0)
        ftp.storbinary('STOR %s' % filename, io.BytesIO(writer.getvalue().encode()))
        ftp.close()
        return True