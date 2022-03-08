from odoo import api, fields, models


class L10nEcSriTaxFormSet(models.Model):
	_name = "l10n.ec.sri.tax.form.set"
	_order = "date_from"

	def prepare_sri_declaration(self):
		for set in self:
			invoices = set.in_invoice_ids + set.in_refund_ids + \
			           set.out_invoice_ids + set.out_refund_ids
			for inv in invoices:
				inv.button_prepare_sri_declaration()

	def get_invoices(self):
		for set in self:
			# Obtenemos todas las facturas abiertas y pagadas del periodo.
			invoices = self.env["account.move"].search([
				("state", "=", "posted"),
				("invoice_date", ">=", set.date_from),
				("invoice_date", "<=", set.date_to),
			])
			no_declarado = invoices.filtered(
				lambda x: x.l10n_latam_document_type_id.code == "NA")
			invoices -= no_declarado
			out_invoice = invoices.filtered(
				lambda x: x.move_type == "out_invoice")
			# Agregamos las devoluciones en venta sin valor a las ventas
			# puesto que así se ingresan las retenciones de tarjeta de crédito.
			out_invoice += invoices.filtered(
				lambda x: x.subtotal == 0 and x.type == "out_refund")
			# Restamos las facturas ya procesadas para mejorar el rendimiento.
			invoices -= out_invoice
			in_invoice = invoices.filtered(lambda x: x.type == "in_invoice")
			invoices -= in_invoice
			# No restamos lo procesado porque la lista es pequeña.
			in_refund = invoices.filtered(lambda x: x.type == "in_refund")
			out_refund = invoices.filtered(lambda x: x.type == "out_refund")
			set.update({
				"no_declarado_ids": no_declarado,
				"out_invoice_ids": out_invoice,
				"out_refund_ids": out_refund,
				"in_invoice_ids": in_invoice,
				"in_refund_ids": in_refund,
			})

	date_from = fields.Date(
		string="Desde",
		required=True
	)
	date_to = fields.Date(
		string="Hasta",
		required=True
	)
	sri_tax_form_ids = fields.One2many(
		"l10n_ec_sri.tax.form",
		inverse_name="sri_tax_form_set_id",
		string="Tax declarations"
	)
	no_declarado_ids = fields.Many2many(
		"account.move",
		"no_declarado_tax_form_set_rel",
		"no_declarado_ids",
		"no_declarado_tax_form_set_ids",
		string="Comprobantes no declarados"
	)
	in_invoice_ids = fields.Many2many(
		"account.move",
		"in_inv_tax_form_set_rel",
		"in_invoice_ids",
		"in_inv_tax_form_set_ids",
		string="In invoices"
	)
	out_invoice_ids = fields.Many2many(
		"account.move",
		"out_inv_tax_form_set_rel",
		"out_invoice_ids",
		"out_inv_tax_form_set_ids",
		string="Out invoices"
	)
	in_refund_ids = fields.Many2many(
		"account.move",
		"in_ref_tax_form_set_rel",
		"in_refund_ids",
		"in_ref_tax_form_set_ids",
		string="In refunds"
	)
	out_refund_ids = fields.Many2many(
		"account.move",
		"out_ref_tax_form_set_rel",
		"out_refund_ids",
		"out_ref_tax_form_set_ids",
		string="Out refunds",
	)
	in_reembolso_ids = fields.One2many(
		"account.move",
		string="Reembolsos en compras",
		compute="_compute_reembolsos",
		readonly=True
	)

	@api.depends("in_invoice_ids", "out_invoice_ids")
	def _compute_reembolsos(self):
		for f in self:
			f.in_reembolso_ids = f.in_invoice_ids.mapped("reembolso_ids")

