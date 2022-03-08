from odoo import api, fields, models


class SaleOrder(models.Model):
	_inherit = "sale.order"

	guide_id = fields.Many2one(
		"account.remission.guide",
		string="Guide"
	)
