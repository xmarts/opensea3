from odoo import api, fields, models


class StockPicking(models.Model):
	_inherit = "stock.picking"

	guide_id = fields.Many2one(
		"account.remission.guide",
		string="Guide",
	)

	def button_generate_guide(self):
		""" Button to generate remission guide
		:return:
		"""
		return {
			"type": "ir.actions.act_window",
			"res_model": "Remission Guide",
			"context": {
				"default_picking_id": self.id,
				"default_partner_id": self.partner_id.id
			},
			"target": "new",
			"view_mode": "form",
		}

	def action_generate_edocument(self):
		for picking in self:
			if picking.guide_id:
				picking.guide_id.action_generate_edocument()