# -*- coding: utf-8 -*-

from odoo import fields, models, api, registry
from odoo.addons.smile_log.tools import SmileDBLogger
import sys


class IrModelImport(models.Model):
    _inherit = 'ir.model.import'

    def _get_state(self, pid):
        with registry(self._cr.dbname).cursor() as new_cr:
            self = self.with_env(self.env(cr=new_cr))
            new_cr.execute("select error_occured from error_history where current_import_id={}".format(pid))
            res = new_cr.fetchone()
            if res!=None:
                return res[0]
        return False

    def _update_template(self, template):
        with registry(self._cr.dbname).cursor() as new_cr:
            self = self.with_env(self.env(cr=new_cr))
            new_cr.execute("update ir_model_import_template set id_current_import={0} where id={1}".format(self.id, template.import_tmpl_id.id))
        return True        

    def _process(self):
        self._update_template(self)
        logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)
        logger.setLevel(self.log_level)
        self = self.with_context(logger=logger)
        try:
            result = self._execute()    
            if self.test_mode:
                self._cr.rollback()            
            error_on_history = self._get_state(self.id)
            if error_on_history:
                vals = {'state': 'exception', 'to_date': fields.Datetime.now()}
            else:
                vals = {'state': 'done', 'to_date': fields.Datetime.now()}
            
            if self.log_returns:
                vals['returns'] = repr(result)
            self.write(vals)
            return result
        except Exception as e:
            logger.error(repr(e))
            try:
                self.write({
                    'state': 'exception',
                    'to_date': fields.Datetime.now(),
                })
            except Exception:
                logger.warning("Cannot set import to exception")
            e.traceback = sys.exc_info()
            raise    
