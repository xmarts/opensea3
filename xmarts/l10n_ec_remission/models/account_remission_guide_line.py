from odoo import api, fields, models


class AccountRemissionGuideLine(models.Model):
	_name = "account.remission.guide.line"
	_inherit = [
		"account.edocument",
		"mail.thread",
		"mail.activity.mixin"
	]
	_description = "Remission Guides"

	guide_id = fields.Many2one(
		"account.remission.guide",
		string="Guide"
	)
	picking_id = fields.Many2one(
		"stock.picking",
		string="Picking",
		domain="[('state','=','done'), "
		       "('picking_type_id.code','in',('outgoing', 'internal')),"
		       "('guide_id','=', False)]"
	)
	move_id = fields.Many2one(
		"account.move",
		string="Invoice",
		compute="_get_invoice"
	)
	partner_id = fields.Many2one(
		"res.partner",
		string="Partner",
		related="picking_id.partner_id"
	)
	origin = fields.Char(string="Source Document")
	reason_id = fields.Many2one(
		"remission.guide.reason",
		string="Reason"
	)
	route_id = fields.Many2one(
		"account.remission.route",
		string="Route"
	)
	dau = fields.Char(string="DAU")

	@api.depends("picking_id")
	def _get_invoice(self):
		for guide in self:
			guide.move_id = False
			if guide.picking_id:
				invoice_id = self.env["account.move"].search([
					("invoice_origin", "=", guide.picking_id.origin),
					("state", "!=", "cancel")], limit=1)
				guide.move_id = invoice_id.id

	#@api.onchange("provincia_id")
	def _onchange_picking_id(self):
		return {
			"domain": {"picking_id": [("id", "not in", self.guide_id.mapped("picking_id").ids)]}
		}