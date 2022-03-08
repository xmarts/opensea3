from odoo import fields, models


class L10nEcImportFileLine(models.Model):
	_name = "l10n.ec.import.file.line"
	_description = "Import file lines"

	import_id = fields.Many2one(
		"l10n.ec.import.document",
		string="Import",
	)
	attachment = fields.Binary(string="Attachment")
	attachment_name = fields.Char(string="Attachment name")
