# -*- coding: utf-8 -*-
# © 2016 Cristian Salamea <cristian.salamea@ayni.com.ec>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from . import amount_to_text_es


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    check_report_id = fields.Many2one(
        'ir.actions.report',
        'Formato de Cheque'
    )


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    third_party_name = fields.Char(
        'A nombre de Tercero',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    to_third_party = fields.Boolean(
        'A nombre de terceros ?',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    date_to = fields.Date('Fecha Cobro')
    number = fields.Integer('Numero de Cheque')
    bank = fields.Many2one('res.bank','Banco del Cheque')
    check_type = fields.Selection([('posfechado','Posfechado'),
                                    ('dia','Al dia')], string="Tipo" , default='dia')

    @api.onchange('payment_date')
    def onchange_payment_date(self):
        if self.payment_date:
            self.date_to = self.payment_date

    @api.onchange('date_to')
    def onchange_date_to(self):
        if self.date_to and self.date_to > self.payment_date:
            self.check_type = 'posfechado'

    @api.onchange('check_number')
    def onchange_check_number(self):
        if self.check_number:
            self.number = self.check_number

    @api.onchange('amount')
    def _onchange_amount(self):
        if hasattr(super(AccountPayment, self), '_onchange_amount'):
            super(AccountPayment, self)._onchange_amount()
        check_amount_in_words = amount_to_text_es.amount_to_text(self.amount)# noqa
        self.check_amount_in_words = check_amount_in_words

    def do_print_checks(self):
        """
        Validate numbering
        Print from journal check template
        """
        for payment in self:
            report = payment.journal_id.check_report_id
            if payment.env.context.get('active_model') == 'account.cheque':
                modelo = 'account.payment'
            else:
                modelo = payment._name
            report.write({'model': modelo})
            payment.write({'state':'sent'})

            return report.report_action(payment)

    def post(self):
        for rec in self:
            super(AccountPayment,rec).post()
            account_check = rec.env['account.cheque']
            if rec.payment_method_id.code in ['check_printing','batch_payment'] and not rec.payment_type == 'transfer':
                types = 'outgoing'
                date = 'cheque_given_date'
                name = rec.partner_id.name
                if rec.payment_type == 'inbound':
                    types = 'incoming'
                    date = 'cheque_receive_date'
                if rec.to_third_party:
                    name = rec.third_party_name
                last_printed_check = rec.search([
                    ('journal_id', '=', rec[0].journal_id.id),
                    ('check_number', '!=', 0)], order="check_number desc", limit=1)
                if types == 'outgoing':
                    debit = rec.destination_account_id.id
                    credit = rec.journal_id.default_debit_account_id.id
                    date_check = rec.payment_date
                    bank_account = rec.journal_id.default_debit_account_id.id
                    if not rec.check_number:
                        next_check_number = last_printed_check and int(last_printed_check.check_number) + 1 or 1
                        
                    else:
                        next_check_number = rec.check_number
                else :
                    bank_account = ''
                    date_check = rec.date_to
                    credit = rec.partner_id.property_account_receivable_id.id
                    debit = rec.journal_id.default_credit_account_id.id
                    next_check_number = rec.number
                # next_check_number = last_printed_check and last_printed_check.check_number + 1 or 1
                check_id = account_check.create({
                    'name':rec.name,
                    'company_id':rec.company_id.id,
                    'bank_account_id':bank_account,
                    'amount':rec.amount,
                    'payee_user_id':rec.partner_id.id,
                    'cheque_date':date_check,
                    'cheque_receive_date':rec.payment_date,
                    'cheque_given_date':rec.date_to,
                    'credit_account_id':credit,
                    'debit_account_id':debit,
                    'journal_id':rec.journal_id.id,
                    'account_cheque_type': types,
                    'status':'registered',
                    'status1':'registered',
                    'cheque_number':next_check_number,
                    'third_party_name':name,
                    'payment_id': rec.id,
                    # 'date' : rec.date_to,
                    #'invoice_ids': rec.invoice_ids,
                })
                for move in rec.move_line_ids:
                    move.move_id.account_cheque_id = check_id.id
                # check_id._count_account_invoice()