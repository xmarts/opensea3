from odoo import api, fields, models


class L10nEcSriTaxForm(models.Model):
	_name = "l10n.ec.sri.tax.form"
	_order = "Forms"

	state = fields.Selection([
		("draft", "Draft"),
		("done", "Done"),
		("replaced", "Replaced"),
	],
		string="State",
		default="draft"
	)
	form = fields.Selection([
		("101", "101"),
		("103", "103"),
		("104", "104"),
	])
	sri_tax_form_set_id = fields.Many2one(
		"l10n_ec_sri.tax.form.set",
		ondelete="cascade",
		string="Tax Form Set"
	)
	date_from = fields.Date(
		string="From",
		related="sri_tax_form_set_id.date_from"
	)
	date_to = fields.Date(
		string="To",
		related="sri_tax_form_set_id.date_to"
	)
	sri_tax_form_line_ids = fields.One2many(
		"l10n.ec.sri.tax.form.line",
		inverse_name="sri_tax_form_id",
		string="Tax declarations"
	)
	payment_ids = fields.Many2many(
		"account.payment",
		"payment_tax_form_rel",
		"payment_ids",
		"tax_form_ids",
		string="Payments"
	)
	move_ids = fields.Many2many(
		"account.move",
		"move_tax_form_rel",
		"move_ids",
		"tax_form_ids",
		string="Move",
	)

	def get_tax_form_lines(self):
		for f in self:
			# Limpiamos las líneas de impuestos previamente creadas.
			f.sri_tax_form_line_ids.unlink()
			tax_form_lines = []
			# Calculamos los impuestos en ventas.
			in_ref = f.sri_tax_form_set_id.mapped("in_refund_ids")
			in_inv = f.sri_tax_form_set_id.mapped("in_invoice_ids")
			purchases = in_inv + in_ref
			taxes = purchases.mapped("sri_tax_line_ids").filtered(
				lambda r: r.formulario == f.formulario)
			for t in set(taxes.mapped("campo")):
				facturas = in_inv.mapped("sri_tax_line_ids").filtered(
					lambda r: r.campo == t)
				devoluciones = in_ref.mapped(
					"sri_tax_line_ids").filtered(lambda r: r.campo == t)
				bruto = sum(facturas.mapped("base"))
				neto = bruto - sum(devoluciones.mapped("base"))
				impuesto = sum(facturas.mapped("amount")) - \
				           sum(devoluciones.mapped("amount"))
				tax_form_lines.append({
					"sri_tax_form_id": f.id,
					"campo": t,
					"bruto": bruto,
					"neto": neto,
					"impuesto": impuesto,
				})

			# Calculamos los impuestos en compras.
			out_inv = f.sri_tax_form_set_id.mapped("out_invoice_ids")
			out_ref = f.sri_tax_form_set_id.mapped("out_refund_ids")
			sale_inv = out_inv + out_ref

			taxes = sale_inv.mapped("sri_tax_line_ids").filtered(
				lambda r: r.formulario == f.formulario)

			for t in set(taxes.mapped("campo")):
				facturas = out_inv.mapped("sri_tax_line_ids").filtered(
					lambda r: r.campo == t)
				devoluciones = out_ref.mapped(
					"sri_tax_line_ids").filtered(lambda r: r.campo == t)

				bruto = sum(facturas.mapped("base"))
				neto = bruto - sum(devoluciones.mapped("base"))
				impuesto = sum(facturas.mapped("amount")) - \
				           sum(devoluciones.mapped("amount"))

				tax_form_lines.append({
					"sri_tax_form_id": f.id,
					"campo": t,
					"bruto": bruto,
					"neto": neto,
					"impuesto": impuesto,
				})

			for line in tax_form_lines:
				self.env["l10n_ec_sri.tax.form.line"].create(line)
