# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"
    
    def _localization_use_documents(self):
        """ This method is to be inherited by localizations 
        and return True if localization use documents """
        for rec in self:
            return (
                True if rec.country_id == self.env.ref("base.ec")
                else super(ResCompany, self)._localization_use_documents()
            )

    @api.depends("country_id")
    def _compute_ecuadorian_localization(self):
        """ Determines if uses ecuadorian localization"""
        for rec in self:
            return (
                True if rec.country_id == self.env.ref("base.ec")
                else False
            )

    @api.onchange("city_id")
    def _onchange_city_id(self):
        for rec in self:
            if rec.city_id:
                rec.city = self.city_id.name
                rec.zip = self.city_id.zipcode
                rec.state_id = self.city_id.state_id
            elif rec._origin:
                rec.city = False
                rec.zip = False
                rec.state_id = False

    l10n_ec_loc = fields.Boolean(
        string="Ecuadorian Localization",
        compute="_compute_ecuadorian_localization",
        store=True
    )
    country_enforce_cities = fields.Boolean(
        related="country_id.enforce_cities",
        readonly=True
    )
    city_id = fields.Many2one(
        "res.city",
        string="City of Address"
    )
    accountant_id = fields.Many2one(
        "res.partner",
        string="Accountant"
    )
    vat = fields.Char(
	    string="RUC",
	    related="partner_id.vat",
    )
    legal_representative_id = fields.Many2one(
        "res.partner",
        string="Legal Representative"
    )
    property_account_position_id = fields.Many2one(
	    "account.fiscal.position",
	    related="partner_id.property_account_position_id",
	    string="Fiscal Position"
    )
    is_force_keep_accounting = fields.Selection([
        ("SI", "Yes"),
        ("NO", "No")],
        string="Keep Accounting",
	    related="property_account_position_id.is_force_keep_accounting"
    )
    is_special_taxpayer = fields.Selection([
         ("SI", "Yes"),
         ("000", "No")],
        string="Special TaxPayer",
	    related="property_account_position_id.is_special_taxpayer"
    )
    taxpayer_code = fields.Char(
	    string="Taxpayer Code",
	    default="000",
	    help="Authorized Code"
    )
    regime = fields.Boolean(
        string="Microempresa Regime",
	    related="property_account_position_id.regime",
        help="Marcar si la empresa está clasificada "
             "como Contribuyente Microempresas"
    )
    rimpe_regime = fields.Boolean(
        string="Rimpe Regime",
	    related="property_account_position_id.rimpe_regime",
        help="Marcar si la empresa está clasificada "
             "como Contribuyente Microempresas"
    )
    agent = fields.Boolean(
	    related="property_account_position_id.agent",
	    string="Withholding Agent",
        help="Check if the company is withholding agent"
    )
    agent_text = fields.Char(
        string="",
        help="Authorized Code"
    )


