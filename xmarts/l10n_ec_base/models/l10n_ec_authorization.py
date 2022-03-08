from datetime import datetime
import time

from odoo import api, fields, models
from odoo.exceptions import ValidationError, Warning as UserError


class L10nEcAuthorization(models.Model):
	_name = "l10n.ec.authorization"
	_description = "Authorization for documents"
	_order = "expiration_date desc"
	_sql_constraints = [
		(
			"number_unique",
			"unique(partner_id,expiration_date,l10n_latam_document_type_id)",
			u"La relación de autorización, serie entidad,"
			u" serie emisor y tipo, debe ser única."
		),
	]

	def default_get(self, fields):
		return {
			**super(L10nEcAuthorization, self).default_get(fields),
			**dict(partner_id=(
					self.env.context.get("partner_id")
					or self.env.user.company_id.partner_id.id
			), active=True, in_type=self._context.get("in_type", "interno"))
		}

	name = fields.Char(
		string="Authorization Number",
		size=128
	)
	num_start = fields.Integer(string="From")
	num_end = fields.Integer(string="To")
	is_electronic = fields.Boolean(string="Is electronic?")
	expiration_date = fields.Date(string="Expiration date")
	active = fields.Boolean(
		compute="_compute_active",
		string="Sec.Activo",
		store=True,
	)
	in_type = fields.Selection([
		("interno", "Internas"),
		("externo", "Externas")
	],
		string="Internal Type",
		readonly=True,
		change_default=True,
	)
	l10n_latam_document_type_id = fields.Many2one(
		"l10n_latam.document.type",
		string="Document Type",
		required=True
	)
	partner_id = fields.Many2one(
		"res.partner",
		string="Partner",
		required=True,
	)
	journal_id = fields.Many2one(
		"account.journal",
		string="Journal"
	)
	sequence_id = fields.Many2one(
		"ir.sequence",
		string="Sequence",
		help=""" Secuencia Alfanumerica para el 
			documento, se debe registrar cuando 
			pertenece a la compañia """,
		ondelete="cascade"
	)

	@api.depends("l10n_latam_document_type_id", "num_start", "num_end")
	def name_get(self):
		res = []
		for record in self:
			name = u"%s (%s-%s)" % (
				record.l10n_latam_document_type_id.code,
				record.num_start,
				record.num_end
			)
			res.append((record.id, name))
		return res

	@api.depends("expiration_date", "is_electronic")
	def _compute_active(self):
		""" Checks if the auth is not expired
		according to its expiration date """

		for auth in self:
			if auth.is_electronic:
				return
			else:
				if auth.expiration_date:
					now = datetime.strptime(
						str(time.strftime("%Y-%m-%d")), "%Y-%m-%d"
					)
					due_date = datetime.strptime(
						str(auth.expiration_date), "%Y-%m-%d"
					)
					auth.active = now <= due_date

	@api.model
	@api.returns("self", lambda value: value.id)
	def create(self, vals):
		""" REVISAR """
		res = self.search([
			("partner_id", "=", vals["partner_id"]),
			("l10n_latam_document_type_id", "=",
			 vals["l10n_latam_document_type_id"]),
			("active", "=", True)
		])
		if res:
			MSG = (
					u"Ya existe una autorización activa para %s"
					% self.l10n_latam_document_type_id.name
			)
			raise ValidationError(MSG)
		partner_id = self.env.user.company_id.partner_id.id
		if vals["partner_id"] == partner_id:
			typ = self.env["l10n_latam.document.type"].browse(
				vals["l10n_latam_document_type_id"])
			name_type = "{0}_{1}".format(
				vals["name"], vals["l10n_latam_document_type_id"]
			)
			sequence_data = {
				"code": (
						typ.code == "07"
						and "account.withholding"
						or "account.move"
				),
				"name": name_type,
				"padding": 9,
			}
			seq = self.env["ir.sequence"].create(sequence_data)
			vals.update({"sequence_id": seq.id})
		return super().create(vals)

	def unlink(self):
		for auth in self:
			res = self.env["account.move"].search(
				[("auth_inv_id", "=", auth.id)]
			)
			if res:
				raise UserError(
					"This authorization is related to a document. ()".format(
						[i.name for i in res])
				)
		return super().unlink()

	def is_valid_number(self, number):
		""" Validates if number is in range
		[@num_start,@num_end]
		"""

		for auth in self:
			if not auth.is_electronic:
				if auth.num_start <= number <= auth.num_end:
					return True
			return False


