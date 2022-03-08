from odoo import api, fields, models


class GenerateRemissionGuide(models.TransientModel):
	_name = "generate.remission.guide"
	_description = "Wizard to generate remission guide"

	@api.model
	def _get_document_type(self):
		doc_type = self.env["l10n_latam.document.type"].search(
			[("l10n_ec_type", "=", "out_waybill")])
		return doc_type

	picking_id = fields.Many2one(
		"stock.picking",
		string="Picking",
	)
	carrier_id = fields.Many2one(
		"res.partner",
		string="Carrier",
		required=True,
		domain="[('is_carrier','=','True')]"
	)
	license_plate = fields.Char(
		string="License Plate",
		required=True
	)
	company_id = fields.Many2one(
		"res.company",
		string="Company",
		default=lambda self: self.env.user.company_id
	)
	is_electronic_document = fields.Boolean(string="Is electronic document")
	l10n_ec_emission_point_id = fields.Many2one(
		"l10n.ec.stablishment",
		string="Emission Point",
		required=True,
		default=lambda self: self.env.user.l10n_ec_emission_point_id
	)
	l10n_latam_document_type_id = fields.Many2one(
		"l10n_latam.document.type",
		string="Document Type",
		required=True,
		default=lambda self: self._get_document_type()
	)
	date = fields.Date(
		string="Date",
		default=fields.date.today(),
		readonly=True
	)
	date_start = fields.Date(
		string="Delivery date start",
		required=True,
		default=fields.Date.today()
	)
	date_end = fields.Date(
		string="Delivery date end",
		required=True,
		default=fields.Date.today()
	)
	move_id = fields.Many2one(
		"account.move",
		string="Invoice",
		domain="[('move_type','in',('out_invoice','in_invoice'))]"
	)
	partner_id = fields.Many2one(
		"res.partner",
		string="Partner"
	)
	origin = fields.Char(string="Source Document")
	reason_id = fields.Many2one(
		"remission.guide.reason",
		string="Reason",
		required=True
	)
	route_id = fields.Many2one(
		"account.remission.route",
		string="Route",
		required=True
	)
	dau = fields.Char(string="DAU")

	def button_generate_guide(self):
		""" Button to generate remission guide
		:return:
		"""
		self.ensure_one()
		guide_id = self.env["account.remission.guide"].create({
			"company_id": self.company_id.id,
			"carrier_id": self.carrier_id.id,
			"license_plate": self.license_plate,
			"l10n_ec_emission_point_id": self.l10n_ec_emission_point_id.id,
			"l10n_latam_document_type_id":  self.l10n_latam_document_type_id.id,
			"date": self.date,
			"date_start": self.date_start,
			"date_end": self.date_end,
		})
		line_id = self.env["account.remission.guide.line"].create({
			"guide_id": guide_id.id,
			"picking_id": self.picking_id.id,
			"partner_id": self.partner_id.id,
			"reason_id": self.reason_id.id,
			"route_id": self.route_id.id,
			"dau": self.dau
		})
		self.picking_id.write({"guide_id": guide_id.id})


