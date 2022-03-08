from odoo import api, fields, models


class AccountMove(models.Model):
	_inherit = "account.move"

	guide_id = fields.Many2one(
		"account.remission.guide",
		string="Guide"
	)
