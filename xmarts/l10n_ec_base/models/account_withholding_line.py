# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountInvoiceTax(models.Model):
    _name = "account.invoice.tax"
    _description = "Withholding Tax"
    _rec_name = "tax_id"

    name = fields.Char(
        string="Tax Description",
        related="tax_id.name"
    )
    group_id = fields.Many2one(
        related="tax_id.tax_group_id",
        store=True,
        string="Group"
    )
    code = fields.Char(
        related="tax_id.description",
        string="Code",
        store=True
    )
    tax_id = fields.Many2one(
        "account.tax",
        string="Tax",
        ondelete="restrict"
    )
    account_id = fields.Many2one(
        "account.account",
        string="Tax Account",
        required=False,
    )
    account_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic account"
    )
    analytic_tag_ids = fields.Many2many(
        "account.analytic.tag",
        string="Analytic Tags"
    )
    amount = fields.Monetary(string="Tax Amount")
    manual = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="account_id.company_id",
        store=True,
        readonly=True
    )
    sequence = fields.Integer(
        help="Gives the sequence order when "
             "displaying a list of invoice tax."
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True
    )
    base = fields.Monetary(string="Base")
    withholding_id = fields.Many2one(
        "account.withholding",
        string="Withholding",
        index=True
    )
    fiscal_year = fields.Char(
        string="Ejercicio Fiscal",
        size=4,
        default=fields.datetime.now().strftime("%Y")
    )

    @api.onchange("tax_id")
    def _onchange_tax_id(self):
        """ Gets tax account id
        :return: None
        """
        for tax in self:
            if tax.tax_id:
                tax.account_id = (
                        tax.tax_id.invoice_repartition_line_ids[-1].
                        account_id.id or False
                )

    @api.onchange("base", "tax_id")
    def _onchange_tax_amount(self):
        """ Get tax withholding amount based on tax
        :return: None
        """
        for line in self:
            if line.base and line.tax_id:
                line.amount = line.base * line.tax_id.amount / 100

    @api.depends("withholding_id.move_id.invoice_line_ids")
    def _compute_base_amount(self):
        tax_grouped = {}
        for invoice in self.mapped("invoice_id"):
            tax_grouped[invoice.id] = invoice.get_taxes_values()
        for tax in self:
            tax.base = 0.0
            if tax.tax_id:
                key = tax.tax_id.get_grouping_key({
                    "tax_id": tax.tax_id.id,
                    "account_id": tax.account_id.id,
                    "account_analytic_id": tax.account_analytic_id.id,
                    "analytic_tag_ids": tax.analytic_tag_ids.ids or False,
                })

            if tax.invoice_id and key in tax_grouped[tax.invoice_id.id]:
                tax.base = tax_grouped[tax.invoice_id.id][key]["base"]



