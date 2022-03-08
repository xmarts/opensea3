
import base64
import os
import itertools

from io import StringIO
from jinja2 import Environment, FileSystemLoader
from os import path

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ... l10n_ec_einvoice.xades.sri import DocumentXML


class AccountRemissionGuide(models.Model):
	_name = "account.remission.guide"
	_inherit = [
		"account.edocument",
		"mail.thread",
		"mail.activity.mixin"
	]
	_description = "Remission Guides"
	_order = "name desc"

	@api.model
	def _get_document_type(self):
		doc_type = self.env["l10n_latam.document.type"].search(
			[("l10n_ec_type", "=", "out_waybill")])
		return doc_type

	name = fields.Char(
		string="Name",
		copy=False
	)
	is_electronic_document = fields.Boolean(
		string="Is electronic document",
		default=True
	)
	carrier_id = fields.Many2one(
		"res.partner",
		string="Carrier",
		required=True,
		domain="[('is_carrier','=','True')]"
	)
	company_id = fields.Many2one(
		"res.company",
		string="Company",
		default=lambda self: self.env.user.company_id
	)
	origin = fields.Char()
	dest_location = fields.Char()
	l10n_ec_emission_point_id = fields.Many2one(
		"l10n.ec.stablishment",
		string="Emission Point",
		default=lambda self: self.env.user.l10n_ec_emission_point_id
	)
	l10n_latam_document_type_id = fields.Many2one(
		"l10n_latam.document.type",
		string="Document Type",
		required=True,
		default=lambda self: self._get_document_type()
	)
	date = fields.Date(
		string="Emission date",
		default=fields.date.today()
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
	license_plate = fields.Char(
		string="License Plate",
		required=True
	)
	state = fields.Selection([
		("draft", "Draft"),
		("valid", "Valid"),
		("sent", "Sent"),
		("cancel", "Cancel")],
		string="State",
		default="draft"
	)
	line_ids = fields.One2many(
		"account.remission.guide.line",
		"guide_id",
		string="Lines"
	)

	def button_draft(self):
		for guide in self:
			guide.state = "draft"

	def button_action_send_email(self):
		""" Open a window to compose an email, with the edi withholding template
		message loaded with electronic withholding data on pdf and xml.
		"""
		for wh in self:
			template_id = self.env.ref(
				"l10n_ec_remission.email_template_eremision",
				raise_if_not_found=False
			)
			attachment_id = self.env["ir.attachment"].search([
				("name", "=", "{}.xml".format(self.clave_acceso)),
				("res_id", "=", self.id)
			], limit=1)
			# template_id.update(
			# 	{"attachment_ids": [(6, 0, [attachment_id.id])]})
			lang = False
			if template_id:
				lang = template_id._render_lang(wh.ids)[wh.id]
			# if not lang:
			# 	lang = self.get_lang(self.env).code
			compose_form = self.env.ref(
				"mail.email_compose_message_wizard_form",
				raise_if_not_found=False
			)
			ctx = dict(default_model="account.remission.guide",
			           default_res_id=self.id,
			           default_res_model="account.remission.guide",
			           default_use_template=bool(template_id),
			           default_template_id=template_id and template_id.id or False,
			           default_composition_mode="comment"
			           )
			return {
				"name": _("Send Electronic Remission"),
				"type": "ir.actions.act_window",
				"view_mode": "form",
				"res_model": "mail.compose.message",
				"views": [(compose_form.id, "form")],
				"view_id": compose_form.id,
				"target": "new",
				"context": ctx,
			}

	def button_validate(self):
		for guide in self:
			if not guide.line_ids:
				raise ValidationError("There are not lines for the guide")
			guide.name = "{}-{}".format(
				guide.l10n_ec_emission_point_id.emission_point_prefix,
				guide.l10n_ec_emission_point_id.remission_guide_sequence_id.next_by_id()
			)
			for line in guide.line_ids:
				line.move_id.guide_id = guide.id
				line.picking_id.guide_id = guide.id
		return guide.write({"state": "valid"})

	def button_cancel(self):
		for guide in self:
			guide.state = "cancel"
			for line in guide.line_ids:
				line.move_id.guide_id = False
				line.picking_id.guide_id = False

	def action_generate_edocument(self):
		""" """
		for guide in self:
			guide.check_date(guide.date_start)
			#guide.check_before_sent()
			access_key, emission_code = guide._get_codes("account.remission.guide")
			eguide, data = guide.render_document(guide, access_key, emission_code)
			guide_xml = DocumentXML(eguide, 'delivery')
			guide_xml.validate_xml()
			if not guide_xml.validate_xml():
				raise ValidationError("Not Valid Schema")
			xades = self.env["l10n.ec.sri.key"].search([
				("company_id", "=", self.company_id.id)])
			buf = StringIO()
			buf.write(eguide)
			xfile = base64.b64encode(buf.getvalue().encode())
			x_path = "/tmp/"
			if not path.exists(x_path):
				os.mkdir(x_path)
			to_sign_file = open(
				x_path + guide.name+".xml", "w")
			to_sign_file.write(eguide)
			to_sign_file.close()
			signed_document = xades.action_sign(to_sign_file)
			ok, errores = guide_xml.send_receipt(signed_document)
			if not ok:
				raise ValidationError(errores)
			sri_auth = self.env["l10n.ec.sri.authorization"].create({
				"sri_authorization_code": access_key,
				"sri_create_date": self.write_date,
				# "move_id": self.id,
				"env_service": self.company_id.env_service
			})
			self.write({"sri_authorization_id": sri_auth.id})
			auth, m = guide_xml.request_authorization(access_key)
			if not auth:
				msg = " ".join(list(itertools.chain(*m)))
				raise ValidationError(msg)
			auth_eguide = self.render_authorized_edocument(auth)
			self._update_document(auth, [access_key, emission_code])
			buf = StringIO()
			buf.write(auth_eguide)
			xfile = base64.b64encode(buf.getvalue().encode())
			attachment = self.env["ir.attachment"].create({
				"name": "{}.xml".format(access_key),
				"datas": xfile,
				"res_model": self._name,
				"res_id": guide.id
			})

	def _get_access_key(self, name):
		if name == "account.remission.guide":
			ld = str(self.date).split("-")
			numero = getattr(self, "name").replace("-", "")
			doc_date = self.date_start

			ld.reverse()
			fecha = "{0:%d%m%Y}".format(doc_date)
			tcomp = self.l10n_latam_document_type_id.code
			ruc = self.company_id.vat
			codigo_numero = self.get_code()
			tipo_emision = self.company_id.emission_code
			access_key = (
				[fecha, tcomp, ruc],
				[numero, codigo_numero, tipo_emision]
			)
			return access_key

	def render_document(self, document, access_key, emission_code):
		tmpl_path = os.path.join(os.path.dirname(__file__), "templates")
		env = Environment(loader=FileSystemLoader(tmpl_path))
		eguide_tmpl = env.get_template("eremission.xml")
		data = {}
		data.update(self._info_tributaria(document, access_key, emission_code))
		data.update(self._info_guia())
		data.update(self._info_destinatarios())
		edocument = eguide_tmpl.render(data)
		return edocument, data

	def _info_guia(self):
		""" Returns Remission Guide Data"""
		company = self.company_id
		data = {
			"dirEstablecimiento": " ".join(
				(company.partner_id.street or "", company.partner_id.street2 or "")
			),
			"dirPartida": " ".join(
				(company.partner_id.street or "", company.partner_id.street2 or "")
			),
			"razonSocialTransportista": self.carrier_id.name,
			"tipoIdentificacionTransportista": (
				self.carrier_id.l10n_latam_identification_type_id.code),
			"rucTransportista": self.carrier_id.vat,
			"obligadoContabilidad": "SI",
			"contribuyenteEspecial": self.company_id.taxpayer_code, #(self.carrier_id.property_account_position_id.is_special_taxpayer or None),
			"fechaIniTransporte": "{0:%d/%m/%Y}".format(self.date_start),
			"fechaFinTransporte": "{0:%d/%m/%Y}".format(self.date_end),
			"placa": self.license_plate
		}
		# if self.carrier_id.rise:
		# 	data.update({"rise": "Contribuyente Regimen Simplificado RISE"})
		return data

		dests = []
		for line in self.line_ids:
			data = {
				"identificacionDestinatario": line.partner_id.vat,
				"razonSocialDestinatario": line.partner_id.name,
				"dirDestinatario": line.partner_id.street,
				"motivoTraslado": line.reason_id.id,
				"ruta": line.route_id.name,
			}
			if line.dau:
				data.update({"docAduaneroUnico": line.dau})
			# if line.move_id:
			# 	data.update({
			# 		"move_id": line.move_id.id,
			# 		"codDocSustento": line.move_id.l10n_latam_document_code,
			# 		"numDocSustento": line.move_id.l10n_latam_document_number,
			# 		"numAutDocSustento": line.move_id.numero_autorizacion or line.move_id.auth_number,
			# 		"fechaEmisionDocSustento": "{0:%d/%m/%Y}".format(line.move_id.invoice_date),
			# 	})

			details = []
			# Picking Info
			for move in line.picking_id.move_ids_without_package:
				for l in move.move_line_ids:
					d = {
						"codigoInterno": l.product_id.name[:25],
						"codigoAdicional": l.product_id.barcode,
						"descripcion": l.product_id.description,
						"cantidad": l.qty_done
					}
					if l.product_id.tracking == "serial":
						d.update({"serial": l.lot_id.name})
					if l.product_id.tracking == "lot":
						d.update({"lot": l.lot_id.name})
					details.append(d)
			data.update({"details": details})
			dests.append(data)
		return {"destinatarios": dests}

	def _info_destinatarios(self):
		dests = []
		for line in self.line_ids:
			data = {
				"identificacionDestinatario": line.partner_id.vat,
				"razonSocialDestinatario": line.partner_id.name,
				"dirDestinatario": line.partner_id.street,
				"motivoTraslado": line.reason_id.id,
				"ruta": line.route_id.name,
			}
			if line.dau:
				data.update({"docAduaneroUnico": line.dau})
			# if line.move_id:
			# 	data.update({
			# 		"move_id": line.move_id.id,
			# 		"codDocSustento": line.move_id.l10n_latam_document_code,
			# 		"numDocSustento": line.move_id.l10n_latam_document_number,
			# 		"numAutDocSustento": line.move_id.numero_autorizacion or line.move_id.auth_number,
			# 		"fechaEmisionDocSustento": "{0:%d/%m/%Y}".format(line.move_id.invoice_date),
			# 	})

			details = []
			# Picking Info
			for move in line.picking_id.move_ids_without_package:
				for l in move.move_line_ids:
					d = {
						"codigoInterno": l.product_id.default_code,
						"codigoAdicional": l.product_id.barcode,
						"descripcion": l.product_id.name,
						"cantidad": l.qty_done
					}
					if l.product_id.tracking == "serial":
						d.update({"serial": l.lot_id.name})
					if l.product_id.tracking == "lot":
						d.update({"lot": l.lot_id.name})
					details.append(d)
			data.update({"details": details})
			dests.append(data)
		return {"destinatarios": dests}

	# def _info_destinatarios(self):
	# 	dests = []
	# 	data = {
	# 		"identificacionDestinatario": self.partner_id.vat,
	# 		"razonSocialDestinatario": self.partner_id.name,
	# 		"dirDestinatario": self.partner_id.street,
	# 		"motivoTraslado": self.reason_id.id,
	# 		"ruta": self.route_id.name,
	# 	}
	# 	if self.dau:
	# 		data.update({"docAduaneroUnico": self.dau})
	# 	if self.move_id:
	# 		data.update({
	# 			"move_id": self.move_id.id,
	# 			"codDocSustento": self.move_id.l10n_latam_document_code,
	# 			"numDocSustento": self.move_id.l10n_latam_document_number,
	# 			"numAutDocSustento": self.move_id.numero_autorizacion or self.move_id.auth_number,
	# 			"fechaEmisionDocSustento": "{0:%d/%m/%Y}".format(self.move_id.invoice_date),
	# 		})
	#
	# 		details = []
	# 		# Picking Info
	# 		for move in self.picking_id.move_ids_without_package:
	# 			for l in move.move_line_ids:
	# 				d = {
	# 					"codigoInterno": l.product_id.name[:25],
	# 					"codigoAdicional": l.product_id.barcode,
	# 					"descripcion": l.product_id.description,
	# 					"cantidad": l.qty_done
	# 				}
	# 				if l.product_id.tracking == "serial":
	# 					d.update({"serial": l.lot_id.name})
	# 				if l.product_id.tracking == "lot":
	# 					d.update({"lot": l.lot_id.name})
	# 				details.append(d)
	# 		data.update({"details": details})
	# 		dests.append(data)
	# 	return {"destinatarios": dests}

	# @api.onchange("partner_id")
	# def _onchange_dest_location(self):
	# 	for line in self:
	# 		line.dest_location = line.partner_id.street

	@api.depends("picking_id")
	def _get_invoice(self):
		for guide in self:
			guide.move_id = False
			if guide.picking_id:
				invoice_id = self.env["account.move"].search([
					("invoice_origin", "=", guide.picking_id.origin),
					("state", "!=", "cancel")], limit=1)
				guide.move_id = invoice_id.id
