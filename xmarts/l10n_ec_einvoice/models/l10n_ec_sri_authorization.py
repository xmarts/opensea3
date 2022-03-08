# from barcode import generate
# from barcode.writer import ImageWriter
import base64
from io import BytesIO

from odoo import api, fields, models


class L10nEcSriAuthorization(models.Model):
	_name = "l10n.ec.sri.authorization"
	_description = "SRI Authorization"
	_rec_name = "sri_authorization_code"
	_order = "sri_create_date"

	sri_authorization_code = fields.Char(string="Authorization Code")
	sri_create_date = fields.Datetime(string="Create Date")
	sri_authorization_date = fields.Char(string="Authorization Date")
	processed = fields.Boolean(default=False)
	env_service = fields.Selection([
		("1", "Test"),
		("2", "Production")],
		string="Environment Type",
		required=True,
	)
	res_id = fields.Integer(string="Document ID")
	res_model = fields.Char(string="Document Model")
	l10n_latam_document_type_id = fields.Many2one(
		"l10n_latam.document.type",
		string="Document Type",
	)
	state = fields.Selection([
		("NO ENVIADO", "NO ENVIADO"),
		("EMITIDA", "EMITIDA"),
		("EN PROCESO", "EN PROCESO"),
		("DEVUELTA", "DEVUELTA"),
		("AUTORIZADO", "AUTORIZADO"),
		("NO AUTORIZADO", "NO AUTORIZADO"),
		("RECHAZADA", "RECHAZADA"),
		("POR ANULAR", "POR ANULAR"),
		("ANULADA", "ANULADA")],
		string="Estado de Autorización",
	)
	barcode = fields.Binary(string="Barcode")
	xml_file = fields.Binary(string="Xml File")
	xml_filename = fields.Char(string="Xml Filename")
	# error_code = fields.Selection(
	# 	[
	# 		("2", "RUC del emisor NO se encuentra ACTIVO"),
	# 		("2", "Production")
	# 	],
	# 	string="Environment Type",
	# 	required=False,
	# )

	reference = fields.Reference(
		string="Reference",
		selection=[],#"_selection_target_model",
		#compute="_compute_resource_ref",
		#inverse="_set_resource_ref"
	)

	@api.model
	def _selection_target_model(self):
		for auth in self:
			auth.reference = '%s,%s' % (auth.res_model, auth.res_id or 0)

	def get_barcode_128(self, clave_acceso):
		# if self.claveacceso:
		# file_data = io.StringIO()
		file_data = BytesIO()
		generate('code128', u'{}'.format(clave_acceso),
		         writer=ImageWriter(),
		         output=file_data)
		file_data.seek(0)
		# self.barcode128 = base64.encodebytes(file_data.read())  # base64.encodestring(file_data.read())
		return base64.encodebytes(file_data.read())  # base64.encodestring(file_data.read())





