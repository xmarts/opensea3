# -*- coding: utf-8 -*-
import base64
import itertools
import os

from io import StringIO
from jinja2 import Environment, FileSystemLoader
from os import path
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from . import utils
from ..xades.sri import DocumentXML

tpIdProv = {
	"l10n_ec_base.ec_ruc": "02",
	"l10n_ec_base.ec_id": "01",
	"l10n_latam_base.it_pass": "02",
	"l10n_ec_base.ec_ex": "02",

}


class AccountMove(models.Model):
	_name = "account.move"
	_inherit = ["account.move", "account.edocument"]
	TEMPLATES = {
		"in_invoice": "liq_purchase.xml",
		"out_invoice": "out_invoice.xml",
		"out_refund": "out_refund.xml",
		"liq_purchase": "liq_purchase.xml",
		"out_debit": "debit_note.xml"
	}
	NAME = {
		"out_invoice": "FACTURA",
		"out_refund": "NC",
		"in_invoice": "LIQ",
		"out_debit": "ND"
	}

	def _info_factura(self, inv):
		""" Arma estructura con datos de cliente proveedor e impuestos
		:param invoice: record(account.move)
		:return:
		"""
		co = inv.company_id
		pa = inv.partner_id
		infoFactura = {
			"fechaEmision": inv.invoice_date.strftime("%d/%m/%Y"),
			"dirEstablecimiento": "{},{}".format(co.street, co.street2),
			"contribuyenteEspecial": co.taxpayer_code,
			"obligadoContabilidad": co.is_force_keep_accounting,
			"tipoIdentificacionComprador": pa.l10n_latam_identification_type_id.code,
			"razonSocialComprador": pa.name,
			"identificacionComprador": pa.vat,
			"direccionComprador": pa.street,
			"totalSinImpuestos": "%.2f" % (inv.amount_untaxed),
			"totalDescuento": "0.00",
			"propina": "0.00",
			"importeTotal": "{:.2f}".format(inv.amount_total),
			"moneda": "DOLAR",
			"formaPago": inv.l10n_ec_sri_payment_id.code,
			# Van en 0 porque no se hace retención
			"valorRetIva": "0.00",
			"valorRetRenta": "0.00",
		}
		if inv.move_type == "in_invoice":
			infoFactura.update({
				"tipoIdentificacionProveedor": pa.l10n_latam_identification_type_id.code,
				"razonSocialProveedor": pa.name,
				"direccionProveedor": pa.street,
				"identificacionProveedor": pa.vat
			})

		totalConImpuestos = []
		totalImpuesto = dict()
		for tax in inv.line_ids.tax_ids:
			if tax.tax_group_id.l10n_ec_type in (
					"vat12", "vat14", "zero_vat",
					"exempt_vat", "ice"
			):
				totalImpuesto = {
					"codigo": utils.tabla16[tax.tax_group_id.l10n_ec_type],
					"codigoPorcentaje": utils.tabla17[str(int(abs(tax.amount)))],
					"baseImponible": "{:.2f}".format(inv.amount_untaxed),
					"tarifa": tax.amount,
					"valor": "{:.2f}".format(inv.amount_tax)
				}
		totalConImpuestos.append(totalImpuesto)
		infoFactura.update({"totalConImpuestos": totalConImpuestos})
		if inv.move_type == "out_refund":
			invoice = inv.reversed_entry_id
			notacredito = {
				"codDocModificado": "01",  # inv.auth_inv_id.type_id.code,
				"numDocModificado": invoice.l10n_latam_document_number,
				"motivo": inv.ref,
				"fechaEmisionDocSustento": inv.invoice_date.strftime("%d/%m/%Y"),
				"valorModificacion": inv.amount_total
			}
			infoFactura.update(notacredito)
		if inv.debit_origin_id:
			invoice = inv.debit_origin_id
			notadebito = {
				"codDocModificado": "01", #Modificar
				"numDocModificado": invoice.l10n_latam_document_number,
				"motivo": inv.ref,
				"fechaEmisionDocSustento": inv.invoice_date.strftime("%d/%m/%Y"),
				"valorTotal": "{:.2f}".format(invoice.amount_total),
			}
			infoFactura.update(notadebito)
		return infoFactura

	def _detalles(self, inv):
		"""	 Reemplaza caracteres especiales usados en campo descripcion.
        Construye cada linea del detalle recalculando los valores
        construye la estructura de impuestos para cada línea
		:param invoice: record(account.move)
		:return:
		"""

		def fix_chars(code):
			special = [
				[u"%", " "],
				[u"º", " "],
				[u"Ñ", "N"],
				[u"ñ", "n"],
				[u"[", " "],
				[u"]", " "],
				[u"á", "a"],
				[u"é", "e"],
				[u"í", "i"],
				[u"ó", "o"],
				[u"ú", "u"],
				[u"\n", " "],
			]
			for f, r in special:
				code = code.replace(f, r)
			return code

		detalles = []
		for line in inv.invoice_line_ids:
			codigoPrincipal = (
					line.product_id and
					line.product_id.default_code and
					fix_chars(line.product_id.default_code) or "001"
			)
			priced = line.price_unit * (1 - (line.discount or 0.00) / 100.0)
			discount = (line.price_unit - priced) * line.quantity
			detalle = {
				"codigoPrincipal": codigoPrincipal,
				"descripcion": fix_chars(line.name.strip()),
				"cantidad": "%.6f" % (line.quantity),
				"precioUnitario": "%.6f" % (line.price_unit),
				"descuento": "%.2f" % discount,
				"precioTotalSinImpuesto": "%.2f" % (line.price_subtotal)
			}
			impuestos = []
			for tax in line.tax_ids:
				aux = tax.amount / 100
				if tax.tax_group_id.l10n_ec_type in (
						"vat12", "vat14", "zero_vat",
						"exempt_vat", "ice"
				):
					impuesto = {
						"codigo": utils.tabla16[tax.tax_group_id.l10n_ec_type],
						"codigoPorcentaje": utils.tabla17[str(int(tax.amount))],
						"baseImponible": "{:.2f}".format(line.price_subtotal),
						"tarifa": tax.amount,
						"valor": "{:.2f}".format(line.price_subtotal * aux)
					}
					impuestos.append(impuesto)
			detalle.update({"impuestos": impuestos})
			detalles.append(detalle)  
		return {"detalles": detalles}

	def _reembolsos(self, invoice):
		"""	 Construye cada linea de los reembolsos.
		Construye la estructura de impuestos para cada línea
		:param invoice: record(account.move)
		:return:
		"""
		reembolsos = []
		if invoice.refund_line_ids:
			for line in invoice.refund_line_ids:
				if not line.partner_id.l10n_latam_identification_type_id:
					raise ValidationError(
						"You must set identification type "
						"for suppliers in refund lines"
					)
				[partner_type_external_id] = line.partner_id \
					.l10n_latam_identification_type_id \
					.get_external_id().values()
				reembolsoDetalle = {
					"tipoIdentificacionProveedorReembolso": line.partner_id.l10n_latam_identification_type_id.code,
					"identificacionProveedorReembolso": line.partner_id.vat,
					"codPaisPagoProveedorReembolso": line.partner_id.country_id.phone_code,
					"tipoProveedorReembolso": tpIdProv[partner_type_external_id],
					"codDocReembolso": line.l10n_latam_document_type_id.code,
					"estabDocReembolso": line.stablishment,
					"ptoEmiDocReembolso": line.emission_point,
					"secuencialDocReembolso": line.number,
					"fechaEmisionDocReembolso":  line.date.strftime("%d/%m/%Y"),
					"numeroautorizacionDocReemb": line.auth_number,
				}
				detalleImpuestos = {
					"detalleImpuesto": {
					"codigo": '2',
					"codigoPorcentaje": '2',
					"tarifa": '2',
					"baseImponibleReembolso": "{:.2f}".format(line.base_imponible),
					"impuestoReembolso": "{:.2f}".format(0.12),
				}}
				reembolsoDetalle.update({"detalleImpuestos": detalleImpuestos})
				reembolsos.append(reembolsoDetalle)
			return {"reembolsos": reembolsos}

	def _compute_discount(self, detalles):
		total = sum([float(det["descuento"]) for det in detalles["detalles"]])
		return {"totalDescuento": "%.2f" % (total)}

	def render_document(self, invoice, access_key, emission_code):
		"""" Renders XML according to move_type """
		tmpl_path = os.path.join(os.path.dirname(__file__), "templates")
		env = Environment(loader=FileSystemLoader(tmpl_path))
		move = self.move_type
		if (
				self.move_type == "in_invoice" and
				self.l10n_latam_document_code == "03"
		):
			move = "liq_purchase"
		einvoice_tmpl = env.get_template(self.TEMPLATES[move])
		data = {}
		data.update(self._info_tributaria(invoice, access_key, emission_code))
		data.update(self._info_factura(invoice))
		detalles = self._detalles(invoice)  # impuestos
		reembolsos = self._reembolsos(invoice)  # impuestos
		data.update(detalles)
		data.update(self._compute_discount(detalles))
		if reembolsos:
			data.update(reembolsos)
		einvoice = einvoice_tmpl.render(data)
		return einvoice

	# def render_authorized_edocument(self, autorizacion):
	# 	""" Renders authorized XML document"""
	# 	tmpl_path = os.path.join(os.path.dirname(__file__), "templates")
	# 	env = Environment(loader=FileSystemLoader(tmpl_path))
	# 	einvoice_tmpl = env.get_template("authorized_einvoice.xml")
	# 	auth_xml = {
	# 		"estado": autorizacion.estado,
	# 		"numeroAutorizacion": autorizacion.numeroAutorizacion,
	# 		"ambiente": autorizacion.ambiente,
	# 		"fechaAutorizacion": str(autorizacion.fechaAutorizacion),
	# 		"comprobante": autorizacion.comprobante
	# 	}
	# 	auth_invoice = einvoice_tmpl.render(auth_xml)
	# 	return auth_invoice

	def action_generate_edocument(self):
		"""
        Método de generación de factura electrónica, liquidaciónes,
        nota de crédito y débito.
        La generación de la factura y envio de email
        einvoice tiene el código reenderizado al formato xsd del sri
        """

		for inv in self:
			if not inv.company_id.vat:
				raise ValidationError(
					"Debe configurar la identificacion de la compañia"
				)
			if inv.move_type not in ("out_invoice", "out_refund", "in_invoice"):
				continue
			self.check_date(inv.invoice_date)
			#self.check_before_sent()
			access_key, emission_code = self._get_codes(name=self._name)
			einvoice = self.render_document(inv, access_key, emission_code)
			move = inv.move_type
			if (
					self.move_type == "in_invoice" and
					self.l10n_latam_document_code == "03"
			):
				move = "liq_purchase"
			inv_xml = DocumentXML(einvoice, move)
			if not inv_xml.validate_xml():
				raise ValidationError("Not Valid Schema")
			xades = self.env["l10n.ec.sri.key"].search([
				("company_id", "=", self.company_id.id)
			])
			buf = StringIO()
			buf.write(einvoice)
			xfile = base64.b64encode(buf.getvalue().encode())
			x_path = "/tmp/"
			if not path.exists(x_path):
				os.mkdir(x_path)

			to_sign_file = open(
				x_path + self.NAME[inv.move_type] + inv.l10n_latam_document_number+".xml", "w")
			to_sign_file.write(einvoice)
			to_sign_file.close()
			signed_document = xades.action_sign(to_sign_file)
			ok, errores = inv_xml.send_receipt(signed_document)
			if not ok:
				raise ValidationError(errores)

			auth, m = inv_xml.request_authorization(access_key)
			if not auth:
				msg = " ".join(list(itertools.chain(*m)))
				raise ValidationError(msg)
			auth_einvoice = self.render_authorized_edocument(auth)
			self._update_document(auth, [access_key, emission_code])
			buf = StringIO()
			buf.write(auth_einvoice)
			xfile = base64.b64encode(buf.getvalue().encode())
			sri_auth = self.env["l10n.ec.sri.authorization"].create({
				"sri_authorization_code": access_key,
				"sri_create_date": self.write_date,
				"l10n_latam_document_type_id": self.l10n_latam_document_type_id.id,
				"env_service": self.company_id.env_service,
				"xml_file": xfile,
				"xml_filename": "{}.xml".format(access_key),
				#"barcode": self.env["l10n.ec.sri.authorization"].get_barcode_128(access_key),
				"res_id": self.id,
				"res_model": self._name,
			})
			self.write({"sri_authorization_id": sri_auth.id})
			attachment = self.env["ir.attachment"].create({
				"name": "{}.xml".format(access_key),
				"datas": xfile,
				"res_model": self._name,
				"res_id": inv.id
			})

	def action_invoice_sent(self):
		""" Open a window to compose an email, with the edi invoice template
            message loaded with electronic invoice data on pdf and xml.
        """
		self.ensure_one()
		templates = {
			"18": "l10n_ec_einvoice.email_template_einvoice",
			"04": "l10n_ec_einvoice.email_template_ecreditnote",
			"03": "l10n_ec_einvoice.email_template_eliq",
		}
		return self.action_document_send(templates[self.l10n_latam_document_code])

	def show_document_info(self):
		access_key, emission_code = self._get_codes(name=self._name)
		einvoice = self.render_document(self, access_key, emission_code)
		move = self.move_type
		if (
				self.move_type == "in_invoice" and
				self.l10n_latam_document_code == "03"
		):
			move = "liq_purchase"
		inv_xml = DocumentXML(einvoice, move)
		data, datosfactura = inv_xml.consulta_factura(access_key)
		message = ''
		if data:
			mensaje = (
					'Estado documento: '
					+ datosfactura.Estado + '\nAmbiente: '
					+ datosfactura.Ambiente
			)
			mensaje += (
					'\nAutorizacion: '
					+ datosfactura.claveAcceso + '\Fecha Autorizacion: '
					+ str(datosfactura.FechaAutorizacion)
			)
			if (
					datosfactura.Estado == 'AUTORIZADO'
					and not self.sri_authorization.id
			):
				sri_auth = self.env['sri.authorization'].create({
					'sri_authorization_code': access_key,
					'sri_create_date': self.write_date,
				})
				self.write({'sri_authorization': sri_auth.id})
		else:
			mensaje='Documento no ha sido Procesado Electronicamente'
		notification = {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'title': 'Mensaje SRI',
				'message': mensaje,
				'type': 'info',
				'sticky': False,
			},
		}
		return notification


