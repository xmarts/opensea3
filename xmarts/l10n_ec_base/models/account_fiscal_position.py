from odoo import _, api, fields, models


class AccountFiscalPosition(models.Model):
	_inherit = "account.fiscal.position"

	l10n_ec_person_type_id = fields.Many2one(
		"l10n.ec.person.type",
		string="Person Type"
	)
	is_force_keep_accounting = fields.Selection([
		("SI", "Yes"),
		("NO", "No")],
		string="Keep Accounting",
		required="True",
		default="NO"
	)
	is_special_taxpayer = fields.Selection([
		("SI", "Yes"),
		("000", "No")],
		string="Is Special TaxPayer",
		required="True",
		default="000"
	)
	agent = fields.Boolean(string="Agent")
	regime = fields.Boolean(
		string="Microempresa Regime",
		help="Marcar si la empresa está clasificada "
		     "como Contribuyente Microempresas"
	)
	rimpe_regime = fields.Boolean(string="Rimpe Regime")
