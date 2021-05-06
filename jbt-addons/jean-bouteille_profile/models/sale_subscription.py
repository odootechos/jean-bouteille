# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import datetime
import traceback

from dateutil.relativedelta import relativedelta

from odoo import api, models, _

_logger = logging.getLogger(__name__)


class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'

    def _recurring_create_invoice(self, automatic=False):
        auto_commit = self.env.context.get('auto_commit', True)
        cr = self.env.cr
        invoices = self.env['account.move']
        current_date = datetime.date.today()
        imd_res = self.env['ir.model.data']
        template_res = self.env['mail.template']
        if len(self) > 0:
            subscriptions = self
        else:
            domain = [('recurring_next_date', '<=', current_date), '|',
                      ('in_progress', '=', True), ('to_renew', '=', True)]
            subscriptions = self.search(domain)
        subscriptions = subscriptions.filtered(lambda r: r.stage_id.do_invoice)
        if subscriptions:
            sub_data = subscriptions.read(fields=['id', 'company_id'])
            for company_id in set(data['company_id'][0] for data in sub_data):
                sub_ids = [
                    s['id'] for s in sub_data
                    if s['company_id'][0] == company_id
                ]
                subs = self.with_context(
                    company_id=company_id,
                    force_company=company_id).browse(sub_ids)
                context_company = dict(self.env.context,
                                       company_id=company_id,
                                       force_company=company_id)
                for subscription in subs:
                    subscription = subscription[0]
                    # Trick to not prefetch other subscriptions, as the cache
                    #  is currently invalidated at each iteration
                    if automatic and auto_commit:
                        cr.commit()
                    # payment + invoice (only by cron)
                    if subscription.template_id.payment_mode in [
                            'validate_send_payment', 'success_payment'
                    ] and subscription.recurring_total and automatic:
                        try:
                            payment_token = subscription.payment_token_id
                            tx = None
                            if payment_token:
                                invoice_values = subscription.with_context(
                                    lang=subscription.partner_id.lang
                                )._prepare_invoice()
                                new_invoice = self.env[
                                    'account.move'].with_context(
                                        context_company).create(invoice_values)
                                new_invoice.message_post_with_view(
                                    'mail.message_origin_link',
                                    values={
                                        'self': new_invoice,
                                        'origin': subscription
                                    },
                                    subtype_id=self.env.ref('mail.mt_note').id)
                                tx = subscription._do_payment(
                                    payment_token,
                                    new_invoice,
                                    two_steps_sec=False)[0]
                                # commit change as soon as we try the payment
                                #  so we have a trace somewhere
                                if auto_commit:
                                    cr.commit()
                                if tx.state in ['done', 'authorized']:
                                    subscription.send_success_mail(
                                        tx, new_invoice)
                                    msg_body = _(
                                        'Automatic payment succeeded. Payment\
                                         reference: <a href=# data-oe-model=\
                                         payment.transaction data-oe-id=%d>%s\
                                         </a>; Amount: %s. Invoice <a href=# \
                                         data-oe-model=account.move data-oe\
                                         -id=%d>View Invoice</a>.') % (
                                            tx.id, tx.reference, tx.amount,
                                            new_invoice.id)
                                    subscription.message_post(body=msg_body)
                                    if subscription.template_id.payment_mode == 'validate_send_payment':
                                        subscription.validate_and_send_invoice(
                                            new_invoice)
                                    if auto_commit:
                                        cr.commit()
                                else:
                                    _logger.error(
                                        'Fail to create recurring invoice for subscription %s',
                                        subscription.code)
                                    if auto_commit:
                                        cr.rollback()
                                    new_invoice.unlink()
                            if tx is None or tx.state != 'done':
                                amount = subscription.recurring_total
                                date_close = (
                                    subscription.recurring_next_date + relativedelta(
                                        days=subscription.template_id.auto_close_limit or 15))
                                close_subscription = current_date >= date_close
                                email_context = self.env.context.copy()
                                email_context.update({
                                    'payment_token':
                                    subscription.payment_token_id and subscription.payment_token_id.name,
                                    'renewed':
                                    False,
                                    'total_amount':
                                    amount,
                                    'email_to':
                                    subscription.partner_id.email,
                                    'code':
                                    subscription.code,
                                    'currency':
                                    subscription.pricelist_id.currency_id.name,
                                    'date_end':
                                    subscription.date,
                                    'date_close':
                                    date_close
                                })
                                if close_subscription:
                                    model, template_id = imd_res.get_object_reference(
                                        'sale_subscription',
                                        'email_payment_close')
                                    template = template_res.browse(template_id)
                                    template.with_context(
                                        email_context).send_mail(
                                            subscription.id)
                                    _logger.debug(
                                        "Sending Subscription Closure Mail to"
                                        "%s for subscription %s and closing subscription",
                                        subscription.partner_id.email,
                                        subscription.id)
                                    msg_body = _(
                                        'Automatic payment failed after multiple attempts.'
                                        'Subscription closed automatically.')
                                    subscription.message_post(body=msg_body)
                                    subscription.set_close()
                                else:
                                    model, template_id = imd_res.get_object_reference(
                                        'sale_subscription',
                                        'email_payment_reminder')
                                    msg_body = _(
                                        'Automatic payment failed. Subscription set to "To Renew".'
                                    )
                                    if (datetime.date.today() - subscription.recurring_next_date).days in [0, 3, 7, 14]:
                                        template = template_res.browse(
                                            template_id)
                                        template.with_context(
                                            email_context).send_mail(
                                                subscription.id)
                                        _logger.debug(
                                            "Sending Payment Failure Mail to %s"
                                            "for subscription %s and setting subscription to pending",
                                            subscription.partner_id.email,
                                            subscription.id)
                                        msg_body += _(
                                            ' E-mail sent to customer.')
                                    subscription.message_post(body=msg_body)
                                    subscription.set_to_renew()
                            if auto_commit:
                                cr.commit()
                        except Exception:
                            if auto_commit:
                                cr.rollback()
                            # we assume that the payment is run only once a day
                            traceback_message = traceback.format_exc()
                            _logger.error(traceback_message)
                            last_tx = self.env['payment.transaction'].search(
                                [('reference', 'like', 'SUBSCRIPTION-%s-%s' %
                                  (subscription.id,
                                   datetime.date.today().strftime('%y%m%d')))],
                                limit=1)
                            error_message = "Error during renewal of subscription %s (%s)" % (
                                subscription.code,
                                'Payment recorded: %s' % last_tx.reference
                                if last_tx and last_tx.state == 'done' else
                                'No payment recorded.')
                            _logger.error(error_message)

                    # invoice only
                    elif subscription.template_id.payment_mode in [
                            'draft_invoice', 'manual', 'validate_send'
                    ]:
                        try:
                            invoice_values = subscription.with_context(
                                lang=subscription.partner_id.lang
                            )._prepare_invoice()
                            new_invoice = self.env[
                                'account.move'].with_context(
                                    context_company).create(invoice_values)
                            new_invoice.message_post_with_view(
                                'mail.message_origin_link',
                                values={
                                    'self': new_invoice,
                                    'origin': subscription
                                },
                                subtype_id=self.env.ref('mail.mt_note').id)
                            new_invoice.with_context(
                                context_company).compute_taxes()
                            invoices += new_invoice
                            next_date = subscription.recurring_next_date or current_date
                            periods = {
                                'daily': 'days',
                                'weekly': 'weeks',
                                'monthly': 'months',
                                'yearly': 'years'
                            }
                            invoicing_period = relativedelta(
                                **{
                                    periods[subscription.recurring_rule_type]:
                                    subscription.recurring_interval
                                })
                            new_date = next_date + invoicing_period
                            subscription.write({
                                'recurring_next_date':
                                new_date.strftime('%Y-%m-%d')
                            })
                            if subscription.template_id.payment_mode == 'validate_send':
                                subscription.validate_and_send_invoice(
                                    new_invoice)
                            if automatic and auto_commit:
                                cr.commit()
                        except Exception:
                            if automatic and auto_commit:
                                cr.rollback()
                                _logger.exception(
                                    'Fail to create recurring invoice for subscription %s',
                                    subscription.code)
                            else:
                                raise
        return invoices
