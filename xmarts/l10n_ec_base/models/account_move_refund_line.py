
from odoo import api, fields, models


class AccountMoveRefundLine(models.Model):
	_name = "account.move.refund.line"
	_description = "Refund Line for Moves"
	_order = "date desc"

	move_id = fields.Many2one(
		"account.move",
		required=True,
		ondelete="cascade"
	)
	partner_id = fields.Many2one(
		"res.partner",
		string="Partner"
	)
	date = fields.Date(string="Date")
	l10n_latam_document_type_id = fields.Many2one(
		"l10n_latam.document.type",
		string="Document Type",
		required=True
	)
	auth_number = fields.Char(
		string="Authorization Number",
		size=50
	)
	# auth_id = fields.Many2one(
	# 	"account.authorization",
	# 	string="Authorization"
	# )
	stablishment = fields.Char(
		string="Stablishment",
		size=3
	)
	emission_point = fields.Char(
		string="Emission Point",
		size=3
	)
	number = fields.Char(
		string="Document Number",
		size=9
	)
	base_imponible = fields.Float(
		string="Base imponible",
		digits=(16, 2)
	)
	base_gravada = fields.Float(
		string="Base gravada",
		digits=(16, 2)
	)
	base_no_gravada = fields.Float(
		string="Base no gravada",
		digits=(16, 2)
	)
	iva_amount = fields.Float(
		string="Monto I.V.A.",
		compute="_compute_iva_amount"
	)
	ice_amount = fields.Float(
		string="Monto I.C.E.",
		digits=(16, 2)
	)
	total = fields.Float(
		string="Total",
		digits=(16, 2),
		compute="_compute_total",
		store=True
	)

	@api.depends(
		"base_gravada",
		"base_no_gravada",
		"iva_amount",
		"ice_amount",
		"base_imponible"
	)
	def _compute_total(self):
		for refund in self:
			refund.total = (
					refund.base_gravada
					+ refund.iva_amount
					+ refund.ice_amount
					+ refund.base_no_gravada
				)

	@api.depends("base_gravada")
	def _compute_iva_amount(self):
		for refund in self:
			refund.iva_amount = round(refund.base_gravada * 0.12, 2)
