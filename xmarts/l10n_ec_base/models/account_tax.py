# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ec_code_base = fields.Char(
        string="Code base",
        help=""" Tax declaration code of the base
         amount prior to the calculation of the tax """
    )
    l10n_ec_code_applied = fields.Char(
        string="Code applied",
        help=""" Tax declaration code of the resulting
              amount after the calculation of the tax """
    )
    l10n_ec_code_ats = fields.Char(
        string="Code ATS",
        help=""" Tax Identification Code 
             for the Simplified Transactional Annex """
    )
    withholding = fields.Boolean(compute="_compute_withholding")
    account_id = fields.Many2one(
        "account.account",
        string="Tax Account",
        ondelete="restrict",
        help="Account that will be set on invoice tax lines for invoices. "
             "Leave empty to use the expense account.",
    )
    withholding_id = fields.Many2one(
        "account.withholding",
        string="Withholding",
        index=True
    )

    def compute_all(
            self, price_unit, currency=None,
            quantity=1.0, product=None,
            partner=None, is_refund=False,
            handle_price_include=True
    ):
        """
        For Withholding Lines
        :param price_unit:
        :param currency:
        :param quantity:
        :param product:
        :param partner:
        :param is_refund:
        :param handle_price_include:
        :return:
        """
        if self.env.context.get("all"):
            return super(AccountTax, self).compute_all(
                price_unit, currency, quantity, product,
                partner, is_refund, handle_price_include
            )
        elif self.env.context.get("withholding"):
            return super(AccountTax, self.filtered(
                lambda x: x.withholding)).compute_all(
                price_unit, currency, quantity, product,
                partner, is_refund, handle_price_include
            )
        return super(AccountTax, self.filtered(
            lambda x: not x.withholding)).compute_all(
            price_unit, currency, quantity, product,
            partner, is_refund, handle_price_include
        )

    def _compute_withholding(self):
        [rec.update({"withholding": rec.amount < 0}) for rec in self]

    def get_grouping_key(self, invoice_tax_val):
        """ Returns a string that will be used to
        group account.invoice.tax
        sharing the same properties
        Este Metodo NO existe v14, se copio desde la v12  wr"""

        self.ensure_one()
        return str(invoice_tax_val["tax_id"]) + "-" + \
               str(invoice_tax_val["account_id"]) + "-" + \
               str(invoice_tax_val["account_analytic_id"]) + "-" + \
               str(invoice_tax_val.get("analytic_tag_ids", []))


class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"    

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super()._get_tax_vals(company, tax_template_to_tax)
        vals.update({
            "l10n_ec_code_base": self.l10n_ec_code_base,
            "l10n_ec_code_applied": self.l10n_ec_code_applied,
            "l10n_ec_code_ats": self.l10n_ec_code_ats,
        })
        return vals
    
    l10n_ec_code_base = fields.Char(
        string="Code base",
        help="Tax declaration code of the base amount "
             "prior to the calculation of the tax"
    )
    l10n_ec_code_applied = fields.Char(
        string="Code applied",
        help="Tax declaration code of the resulting "
             "amount after the calculation of the tax"
    )
    l10n_ec_code_ats = fields.Char(
        string="Code ATS",
        help="Tax Identification Code for the "
             "Simplified Transactional Annex"
    )
