from odoo import fields, models


class ResCountry(models.Model):
	_inherit = "res.country"

	l10n_ec_country_code = fields.Char(string="Country Code Ec")
