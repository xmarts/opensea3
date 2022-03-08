from odoo import _, api, fields, models


class SriDocumentosElectronicosQueue(models.Model):
	_name = "l10n_ec_sri.documento.electronico.queue"
	_description = "Documentos Electronicos queue"

	name = fields.Char(string="Name")
	queue_line_ids = fields.One2many(
		"l10n_ec_sri.documento.electronico.queue.line",
		"queue_id",
		string="Cola de documentos electrónicos",
	)

	@api.model
	def process_de_queue(self, ids=None):
		queue = self.env.ref("l10n_ec_sri_ece.documento_electronico_queue")
		procesadas = queue.queue_line_ids.filtered(
			lambda x: x.sent == True and x.estado == "AUTORIZADO"
		)

		if procesadas:
			# Usamos try porque es posible que el cron se ejecute
			# al mismo tiempo que una orden manual del usuario
			# y se intente borrar dos veces el mismo record.
			try:
				procesadas.unlink()
			except:
				pass

		pendientes = queue.queue_line_ids
		for p in pendientes:
			de = p.documento_electronico_id
			if de.estado == "NO ENVIADO":
				de.send_de_backend()

			if de.estado in ("RECIBIDA", "EN PROCESO"):
				de.receive_de_offline()

			if not p.sent and p.estado == "AUTORIZADO":
				try:
					sent = de.reference.send_email_de()
					p.sent = sent
				except:
					p.sent = False


class SriDocumentosElectronicosQueueLine(models.Model):
	_name = "l10n_ec_sri.documento.electronico.queue.line"
	_description = "Documentos Electronicos queue line"
	_order = "create_date desc"

	sent = fields.Boolean(string="Sent")
	estado = fields.Selection(
		string="State",
		related="documento_electronico_id.estado",
		store=True
	)
	documento_electronico_id = fields.Many2one(
		"l10n_ec_sri.documento.electronico",
		string="Documento electronico",
	)
	reference = fields.Reference(
		related="documento_electronico_id.reference",
		string=_("Reference")
	)
	queue_id = fields.Many2one(
		"l10n_ec_sri.documento.electronico.queue",
		string="Queue",
	)