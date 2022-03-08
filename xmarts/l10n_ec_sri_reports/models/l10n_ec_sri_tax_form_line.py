from odoo import api, fields, models


class L10nEcSriTaxFormLine(models.Model):
	_name = "l10n.ec.sri.tax.form.line"
	_order = "campo"

	def _compute_tax_lines(self):
		for r in self:
			s = r.sri_tax_form_id.sri_tax_form_set_id
			invoices = s.in_invoice_ids + s.in_refund_ids + \
			           s.out_invoice_ids + s.out_refund_ids
			taxes = invoices.mapped("sri_tax_line_ids")
			r.sri_tax_line_ids = taxes.filtered(lambda x: x.campo == r.campo)

	sri_tax_line_ids = fields.One2many(
		"l10n.ec.sri.tax.line",
		compute=_compute_tax_lines,
		string="Tax lines"
	)
	sri_tax_form_id = fields.Many2one(
		"l10n.ec.sri.tax.form",
		ondelete="cascade",
		string="Tax form",
	)
	name = fields.Char(string="Description")
	campo = fields.Char(string="Campo")
	bruto = fields.Float(
		string="Valor bruto",
		digits=(9, 2)
	)
	neto = fields.Float(
		string="Valor neto",
		digits=(9, 2)
	)
	impuesto = fields.Float(
		string="Impuesto",
		digits=(9, 2)
	)