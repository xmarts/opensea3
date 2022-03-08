try:
	from base64 import encodestring
except ImportError:
	from base64 import encodebytes as encodestring

import calendar
from io import StringIO
from itertools import groupby
from lxml import etree
from lxml.etree import DocumentInvalid
from jinja2 import Environment, FileSystemLoader
from operator import itemgetter
import os

from odoo import api, fields, models

tpIdProv = {
	"l10n_ec_base.ec_ruc": "01",
	"l10n_ec_base.ec_id": "02",
	"l10n_latam_base.it_pass": "03",
	"l10n_ec_base.ec_final": "03"
}
tpIdCliente = {
	"l10n_latam_base.it_pass": "03",
	"l10n_ec_base.ec_ruc": "01",
	"l10n_ec_base.ec_id": "02",
	"l10n_ec_base.ec_final": "04",

}

def convertir_fecha(date):
	"""
	fecha: '2012-12-15'
	return: '15/12/2012'
	"""
	return


class AccountAts(dict):
	"""
	representacion del ATS
	"valor"
	"""
	def __getattr__(self, item):
		try:
			return self.__getitem__(item)
		except KeyError:
			raise AttributeError(item)

	def __setattr__(self, item, value):
		if item in self.__dict__:
			dict.__setattr__(self, item, value)
		else:
			self.__setitem__(item, value)


class AtsWizard(models.TransientModel):
	_name = "ats.wizard"
	_description = "Anexo Transaccional Simplificado"

	fcname = fields.Char(
		string="ATS Filename",
		readonly=True
	)
	data = fields.Binary(string="XML file")
	fcname_errores = fields.Char(
		string="Errors Filename",
		readonly=True
	)
	error_data = fields.Binary(string="Errors File")
	date = fields.Date(
		string="Period",
		default=fields.Date.today()
	)
	company_id = fields.Many2one(
		"res.company",
		string="Company",
		default=lambda self: self.env.user.company_id.id
	)
	num_estab_ruc = fields.Char(
		string="Num. de Establecimientos",
		size=3,
		required=True,
		default="001"
	)
	state = fields.Selection(
		[
			("choose", "Elegir"),
			("export", "Generado"),
			("export_error", "Error")
		],
		string="State",
		default="choose"
	)
	#no_validate = fields.Boolean("No Validar")

	@staticmethod
	def process_lines(lines):
		"""
		@temp: {"332": {baseImpAir: 0,}}
		@data_air: [{baseImpAir: 0, ...}]
		"""
		data_air = []
		temp = {}
		for line in lines:
			if line.group_id.l10n_ec_type == "wh_income_tax":
				if not temp.get(line.base_code_id.code):
					temp[line.base_code_id.code] = {
						"baseImpAir": 0.00,
						"valRetAir": 0.00
					}
				temp[line.base_code_id.code]["baseImpAir"] += line.base_amount
				temp[line.base_code_id.code]["codRetAir"] = line.base_code_id.code  # noqa
				temp[line.base_code_id.code]["porcentajeAir"] = int(line.tax_id.amount)  # noqa
				temp[line.base_code_id.code]["valRetAir"] += abs(line.amount)
		for k, v in temp.items():
			data_air.append(v)
		return data_air

	def _get_ventas(self):
		"TODO SELECT type, sum(amount_vat+amount_vat_cero+amount_novat) AS base"
		self.env.cr.execute(f"""SELECT sum(
                case when move_type = 'out_refund' 
                then amount_total * -1
                else amount_total
                end
            ) AS base
            FROM account_move
            WHERE move_type IN ('out_invoice', 'out_refund')
                AND state = 'posted'
                AND  EXTRACT(MONTH FROM date) = {self.date.month}
                AND  EXTRACT(YEAR FROM date) = {self.date.year}
            GROUP BY move_type""")
		res = self.env.cr.fetchone()
		return res and res[0] or 0.00

	def _get_reembolsos(self, inv):
		"""
		REVISAR PORQUE ACÁ PUEDEN IR TAMBIÉN LAS NOTAS DE CRÉDITO
		:param invoice:
		:return:
		"""
		res = []
		if inv.refund_move_ids:
			for r in inv.refund_move_ids:
				[partner_type_external_id] = r.partner_id \
					.l10n_latam_identification_type_id \
					.get_external_id().values()
				res.append({
					"tipoComprobanteReemb": r.l10n_latam_document_type_id.code,
					"tpIdProvReemb": tpIdProv[partner_type_external_id],
					"idProvReemb": r.partner_id.vat,
					"establecimientoReemb": r.l10n_latam_document_number[0:3],
					"puntoEmisionReemb": r.l10n_latam_document_number[4:7],
					"secuencialReemb": r.l10n_latam_document_number[8:17],
					"fechaEmisionReemb": convertir_fecha(r.invoice_date),
					"autorizacionReemb": r.auth_number,
					"baseImponibleReemb": "{:.2f}".format(inv.amount_untaxed),
					"baseImpGravReemb": 0.00,#"%.2f" % r.base_gravada,
					"baseNoGravReemb": 0.00,#"%.2f" % r.base_no_gravada,
					"baseImpExeReemb": 0.00,#"0.00",
					"montoIceRemb": 0.00,#"%.2f" % r.ice_amount,
					"montoIvaRemb": 0.00#"%.2f" % r.iva_amount
				})
			return res

	def read_compras(self):
		"""
		Procesa:
		  * Facturas de proveedor
		  * Liquidaciones de compra
		"""
		compras = []
		f, l = calendar.monthrange(self.date.year, self.date.month)
		for inv in self.env["account.move"].with_context(all=True).search([
			("state", "=", "posted"),
			("invoice_date", ">=",  self.date.replace(day=f)),
			("invoice_date", "<=",  self.date.replace(day=l)),
			("move_type", "in", ("in_invoice", "in_refund"))
		]):
			if (
					inv.partner_id.l10n_latam_identification_type_id
					== self.env.ref("l10n_latam_base.it_pass")
			):
				continue
			amount_tax_code = inv._amounts_by_tax_group()
			_get_amount = lambda code, signal: amount_tax_code.get(
				code, {}
			).get(signal, 0.00)
			amount_by_wh = inv._get_ret_iva()
			if (not inv.auth_inv_id.l10n_latam_document_type_id.code
			        in ("41", "03")):
				t_reeb = 0.00
			else:
				t_reeb = inv.amount_untaxed
			[partner_type_external_id] = inv.partner_id \
				.l10n_latam_identification_type_id \
				.get_external_id().values()
			detallecompras = {
				"codSustento": inv.support_id.code,
				"tpIdProv": tpIdProv[partner_type_external_id],
				"idProv": inv.partner_id.vat,
				"tipoComprobante": inv.auth_inv_id.l10n_latam_document_type_id.code,  # noqa
				"parteRel": "NO",
				"fechaRegistro": convertir_fecha(inv.invoice_date),
				"establecimiento": inv.l10n_latam_document_number[:3],
				"puntoEmision": inv.l10n_latam_document_number[4:6],
				"secuencial": inv.l10n_latam_document_number[7:17],
				"fechaEmision": convertir_fecha(inv.invoice_date),
				"autorizacion": inv.auth_number,
				"baseNoGraIva": f"{_get_amount('not_charged_vat', 'base')}",
				"baseImponible": f"{_get_amount('zero_vat', 'base')}",
				"baseImpGrav": f"{_get_amount('vat12', 'base')}",
				"baseImpExe": f"{_get_amount('exempt_vat', 'base')}",
				"total": inv.amount_total,
				"montoIce": "0.00",
				"montoIva": "%.2f" % inv.amount_tax,
				"valRetBien10": f"%.2{amount_by_wh.get('wh_vat_assets10') or 0.00}",
				"valRetServ20": f"%.2{amount_by_wh.get('wh_vat_services20') or 0.00}",
				"valorRetBienes": f"%.2{amount_by_wh.get('wh_vat_assets') or 0.00}",
				"valRetServ50": f"%.2{amount_by_wh.get('wh_vat_services50') or 0.00}",
				"valorRetServicios": f"%.2{amount_by_wh.get('wh_vat_services') or 0.00}",
				"valRetServ100": f"%.2{amount_by_wh.get('wh_vat_services100') or 0.00}",
				"totbasesImpReemb": "%.2f" % t_reeb,
				"pagoExterior": {
					"pagoLocExt": "01",
					"paisEfecPago": "NA",
					"aplicConvDobTrib": "NA",
					"pagoExtSujRetNorLeg": "NA"
				},
				"formaPago": inv.l10n_ec_sri_payment_id.code,
				#"detalleAir": self.process_lines(inv.withholding_id.tax_ids),
			}
			if inv.withholding_id:
				detallecompras.update(inv.withholding_id._get_at_wh())
			# if inv.move_type in ("out_refund", "in_refund"):
			#     detallecompras.update(inv.get_ats_refund())
			detallecompras.update({
				"reembolsos": self._get_reembolsos(inv)
			})
			compras.append(detallecompras)
		return compras

	def read_ventas(self):
		ventas = []
		f, l = calendar.monthrange(self.date.year, self.date.month)
		for inv in self.env["account.move"].with_context(all=True).search([
			("state", "=", "posted"),
			("invoice_date", ">=", self.date.replace(day=f)),
			("invoice_date", "<=", self.date.replace(day=l)),
			("move_type", "=", "out_invoice"),
		]):
			[partner_type_external_id] = inv.partner_id \
				.l10n_latam_identification_type_id \
				.get_external_id().values()

			amount_tax_code = inv._amounts_by_tax_group()
			_get_amount = lambda code, signal: amount_tax_code.get(
				code, {}
			).get(signal, 0.00)
			detalleventas = {
				"tpIdCliente": tpIdCliente[partner_type_external_id],
				"idCliente": inv.partner_id.vat,
				"parteRelVtas": "NO",
				"partner": inv.partner_id,
				"auth": inv.auth_inv_id,
				"tipoComprobante": inv.l10n_latam_document_code,
				"tipoEmision": "E", #inv.auth_inv_id.is_electronic and "E" or "F",
				"numeroComprobantes": 1,
				"baseNoGraIva": _get_amount('not_charged_vat', 'base'),
				"baseImponible": _get_amount('zero_vat', 'base'),
				"baseImpGrav": abs(_get_amount('vat12', 'base')),
				"montoIva": _get_amount('vat12', 'amount'),
				"montoIce": "0.00",
				"valorRetIva": (
						abs(_get_amount('wh_vat_assets', 'amount')) +
						abs(_get_amount('wh_vat_services', 'amount'))
				),  # noqa
				"valorRetRenta": abs(_get_amount('wh_income_tax', 'amount')),
				"formasDePago": {
					"formaPago": inv.l10n_ec_sri_payment_id.code
				}
			}
			ventas.append(detalleventas)
		ventas = sorted(ventas, key=itemgetter("idCliente"))
		ventas_end = []
		for ruc, grupo in groupby(ventas, key=itemgetter("idCliente")):
			baseimp = 0
			nograviva = 0
			montoiva = 0
			retiva = 0
			impgrav = 0
			retrenta = 0
			numComp = 0
			auth_temp = False
			for i in grupo:
				nograviva += i["baseNoGraIva"]
				baseimp += i["baseImponible"]
				impgrav += i["baseImpGrav"]
				montoiva += i["montoIva"]
				retiva += i["valorRetIva"]
				retrenta += i["valorRetRenta"]
				numComp += 1
				auth_temp = i["auth"]
			detalle = {
				"tpIdCliente": tpIdCliente[partner_type_external_id],
				"idCliente": ruc,
				"parteRelVtas": "NO",
				"tipoComprobante": auth_temp.l10n_latam_document_type_id.code,
				"tipoEmision": auth_temp.is_electronic and "E" or "F",
				"numeroComprobantes": numComp,
				"baseNoGraIva": "%.2f" % nograviva,
				"baseImponible": "%.2f" % baseimp,
				"baseImpGrav": "%.2f" % abs(impgrav),
				"montoIva": "%.2f" % montoiva,
				"montoIce": "0.00",
				"valorRetIva": "%.2f" % retiva,
				"valorRetRenta": "%.2f" % retrenta,
				"formasDePago": {
					"formaPago": inv.l10n_ec_sri_payment_id.code or "20"
				}
			}
			ventas_end.append(detalle)
		return ventas_end

	def read_anulados(self):
		f, l = calendar.monthrange(self.date.year, self.date.month)
		dmn = [
			("state", "=", "cancel"),
			("invoice_date", ">=", self.date.replace(day=f)),
			("invoice_date", "<=", self.date.replace(day=l)),
			("move_type", "=", "out_invoice")
		]
		anulados = []
		for inv in self.env["account.move"].search(dmn):
			aut = inv.numero_autorizacion or inv.auth_number
			detalleanulados = {
				"tipoComprobante": inv.l10n_latam_document_type_id.code,
				"establecimiento": inv.l10n_latam_document_number[:3],
				"ptoEmision": inv.l10n_latam_document_number[4:6],
				"secuencialInicio": inv.l10n_latam_document_number[6:9],
				"secuencialFin": inv.l10n_latam_document_number[6:9],
				"autorizacion": aut
			}
			anulados.append(detalleanulados)
		for wh in self.env["account.withholding"].search([
			("state", "=", "cancel"),
			("date", ">=", self.date.replace(day=f)),
			("date", "<=", self.date.replace(day=l)),
			("withholding_type", "=", "ret_in_invoice")
		]):
			aut = inv.numero_autorizacion #or auth.name
			anulados.append({
				"tipoComprobante": wh.l10n_latam_document_type_id.code,
				"establecimiento": wh.move_id.journal_id.l10n_ec_entity,
				"ptoEmision": wh.move_id.journal_id.l10n_ec_emission,
				"secuencialInicio": wh.name[6:9],
				"secuencialFin": wh.name[6:9],
				"autorizacion": aut
			})
		return anulados

	@staticmethod
	def fix_chars(code):
		special = [
			[u'Á', 'A'],
			[u'É', 'E'],
			[u'Í', 'I'],
			[u'Ó', 'O'],
			[u'Ú', 'U'],
			[u'Ñ', 'N'],
			[u'ñ', 'n'],
			[u'-', ''],
			[u'.', '']

		]
		for f, r in special:
			code = code.replace(f, r)
		return code

	@staticmethod
	def render_xml(ats):
		""" Renders xml"""
		tmpl_path = os.path.join(os.path.dirname(__file__), "templates")
		env = Environment(loader=FileSystemLoader(tmpl_path))
		ats_tmpl = env.get_template("ats.xml")
		return ats_tmpl.render(ats)

	@staticmethod
	def validate_document(ats, error_log=False):
		file_path = os.path.join(os.path.dirname(__file__), "XSD/ats.xsd")
		schema_file = open(file_path)
		xmlschema_doc = etree.parse(schema_file)
		xmlschema = etree.XMLSchema(xmlschema_doc)
		root = etree.fromstring(ats.encode())
		ok = True
		""" VER QUÉ HACE ESTO DE NO VALIDATE"""
		## if not self.no_validate:
		try:
			xmlschema.assertValid(root)
		except DocumentInvalid:
			ok = False
		return ok, xmlschema

	def act_export_ats(self):
		""" Generates ATS Report"""

		ats = AccountAts()
		total_sales = self._get_ventas()
		ruc = self.company_id.partner_id.vat
		ats.TipoIDInformante = "R"
		ats.IdInformante = ruc
		ats.razonSocial = self.fix_chars(self.company_id.name.upper())
		ats.Anio = self.date.year
		ats.Mes = str(self.date.month).zfill(2)
		ats.numEstabRuc = self.num_estab_ruc.zfill(3)
		ats.AtstotalVentas = "{:.2f}".format(total_sales)
		ats.totalVentas = "{:.2f}".format(total_sales)
		ats.codigoOperativo = "IVA"
		ats.compras = self.read_compras()
		ats.ventas = self.read_ventas()
		ats.codEstab = self.num_estab_ruc
		ats.ventasEstab = "{:.2f}".format(total_sales)
		ats.ivaComp = "0.00"
		ats.anulados = self.read_anulados()
		ats_rendered = self.render_xml(ats)
		ok, schema = self.validate_document(ats_rendered)
		buf = StringIO()
		buf.write(ats_rendered)
		out = encodestring(buf.getvalue().encode("utf-8")).decode()
		buf.close()
		buf_erro = StringIO()
		buf_erro.write("\n".join([
			error_log.message for error_log in schema.error_log
		]))
		out_erro = encodestring(buf_erro.getvalue().encode())
		buf_erro.close()
		data2save = {
			"state": ok and "export" or "export_error",
			"data": out,
			"fcname": f"ATS_{self.date}.XML"
		}
		if not ok:
			data2save.update({
				"error_data": out_erro,
				"fcname_errores": "ERRORES.txt"
			})
		self.write(data2save)
		view_id = self.env.ref("l10n_ec_sri_reports.wizard_export_ats_form").id
		return {
			"type": "ir.actions.act_window",
			"name": "ATS",
			"view_mode": "form",
			"res_model": "ats.wizard",
			"target": "new",
			"res_id": self.id,
			"views": [[view_id, "form"]],
		}