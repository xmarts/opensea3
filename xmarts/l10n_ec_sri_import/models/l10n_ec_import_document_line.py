
from odoo import api, fields, models, _


class L10nEcImportDocumentLine(models.Model):
	_name = "l10n.ec.import.document.line"
	_description = "Import file"

	import_id = fields.Many2one(
		"l10n.ec.import.document",
		string="Import",
	)
	l10n_latam_document_type_id = fields.Many2one(
		"l10n_latam.document.type",
		string="Document Type",
	)
	emission_date = fields.Date(string="Emission Date")
	l10n_latam_document_number = fields.Char(string="Document Number")
	modified_document_number = fields.Char(string="Modified Document Number")
	authorization_code = fields.Char(string="Authorization Code")
	access_key = fields.Char(string="Access Key")
	amount = fields.Float(string="Amount")
	partner_id = fields.Many2one(
		"res.partner",
		string="Partner",
	)
	partner_name = fields.Char(
		string="Partner name",
		readonly=True
	)
	reconciled_sri = fields.Boolean(string="Reconciled SRI")
	vat = fields.Char(
		string="Vat",
		readonly=True
	)
	xml = fields.Binary(
		string="XML",
		readonly=True
	)
	move_id = fields.Many2one("account.move", string="Invoice")
	withholding_id = fields.Many2one(
		"account.withholding",
		string="Withholding"
	)

	def validate_document(self):
		#for line in self:

		pass
