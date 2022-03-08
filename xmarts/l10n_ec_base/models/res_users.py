from odoo import api, fields, models


class ResUsers(models.Model):
	_inherit = "res.users"

	l10n_ec_emission_point_id = fields.Many2one(
		"l10n.ec.stablishment",
		string="Emission Point"
	)
