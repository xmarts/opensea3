# -*- coding: utf-8 -*-

import base64
import calendar
import datetime

from io import StringIO
from itertools import groupby
from operator import itemgetter
from xlwt import Workbook, easyxf

from odoo import api, fields, models
from odoo.tools import ustr


def get_style(bold=False, font_name='Calibri', height=12, font_color='black',
              rotation=0, align='center',
              border=True, color=None, format=None):
	str_style = 'font: bold %s, name %s, height %s, color %s;'%(bold, font_name, height*20, font_color)
	str_style += 'alignment: rotation %s, horizontal %s, vertical center, wrap True;'%(rotation, align)
	str_style += border and 'border: left thin, right thin, top thin, bottom thin;' or ''
	str_style += color and 'pattern: pattern solid, fore_colour %s;'%color or ''
	return easyxf(str_style, num_format_str = format)


def style(bold=False, font_name="Calibri", size=10, font_color="black",
          rotation=0, align="left", height=12,
          border=False, color=None, format=None):
	return get_style(bold, font_name, height, font_color, rotation, align, border, color, format)


class AccountReportTaxWizard(models.TransientModel):
	_name = "account.report.tax.wizard"
	_description = "Reports 103-104 for tax declaration"

	def _default_end(self):
		today = datetime.date.today()
		first, last = calendar.monthrange(today.year, today.month)
		today = today.replace(day=last)
		res = fields.Date.to_string(today)
		return res

	date_start = fields.Date(
		string="Start Period",
		default=fields.Date.to_string(datetime.date.today().replace(day=1))
	)
	date_end = fields.Date(
		string="End Period",
		default=_default_end
	)

	def period(self):
		ds = fields.Date.from_string(self.date_start)
		period = "{0:02d}-{1}".format(ds.month, ds.year)
		return period

	def action_print(self):

		taxes = []
		wh_ir = []
		wh_vat = []
		nc = []
		vat = []
		sales = []
		sale_vat = []

		sql = """
	        SELECT am.move_type,
			tax.description as code,
	        tax.name as name,
	        atg.l10n_ec_type as gcode,
	        SUM(aml.tax_base_amount) as base,
	        ABS(COALESCE(SUM(aml.debit-aml.credit), 0)) as total
	        FROM account_move_line aml 
	        INNER JOIN account_move am on am.id = aml.move_id
	        INNER JOIN account_tax tax on tax.id = aml.tax_line_id
	        INNER JOIN account_tax_group atg on atg.id = tax.tax_group_id
	        WHERE  tax.id = aml.tax_line_id AND aml.tax_exigible 
	        AND am.date BETWEEN '%s' and '%s' 
	        AND am.state = 'posted'
	        AND am.move_type in ('in_invoice', 'out_invoice',
	        'out_refund', 'in_refund', 'out_debit','in_debit')
	        GROUP BY atg.l10n_ec_type, tax.name, am.move_type, tax.description
	        union all
	        select  am.move_type,
	        tax.description as code,
	        tax.name as name,
	        atg.l10n_ec_type as gcode,
	        SUM(aml.price_subtotal) as base,
	        0 as total
	        from account_move_line_account_tax_rel trm
	        join account_move_line aml on aml.id = trm.account_move_line_id
	        join account_tax tax on tax.id = trm.account_tax_id
	        join account_tax_group atg on atg.id = tax.tax_group_id
	        join account_move am on am.id = aml.move_id
	        where atg.l10n_ec_type = 'zero_vat'
	        AND am.state = 'posted'
	        AND am.date BETWEEN '%s' and '%s' 
	        AND am.move_type in ('in_invoice', 'out_invoice',
	        'out_refund', 'in_refund', 'out_debit','in_debit')
	        group by  atg.l10n_ec_type, tax.name, am.move_type, tax.description
	        ORDER BY code, move_type;
	        """ % (
			self.date_start, self.date_end,
			self.date_start, self.date_end)

		self._cr.execute(sql)
		res = self._cr.fetchall()
		book = Workbook()
		row = 5
		STYLES = {
			'std': style(),
			'bold': style(True, size=12),
			'title': style(True, font_color='white', color='periwinkle', align='center'),
			'%': style(format='0.00%'),
			'num': style(format='[$$-300A]#,##0.00;[$$-300A]-#,##0.00', align='right'),
			'numbold': style(True, format='[$$-300A]#,##0.00;[$$-300A]-#,##0.00', align='right')
		}
		for line, tax in groupby(
				sorted(res, key=lambda x: (x[0], x[3])), lambda x: (x[0], x[3]),
		):
			if line == "out_invoice":
				if tax in ["vat12", "exempt_vat", "zero_vat", "irbp"]:
					sale_vat.append(tax)
				else:
					sales.append(tax)
			elif line in ["in_refund", "out_refund", "out_debit", "in_debit"]:
				nc.append(tax)
			elif tax in ["wh_income_tax", "no_wh_ir"]:
				wh_ir.append(tax)
			elif tax in ["wh_vat", "wh_vat_assets", "wh_vat_services"]:
				wh_vat.append(tax)
			elif tax in ["vat12", "exempt_vat", "zero_vat", "irbp"]:
				vat.append(tax)
			sheet = book.add_sheet("103")
			sheet.write(row, 0, "IMPUESTO AL VALOR AGREGADO VENTAS", STYLES['bold'])
			taxes.append({
				"lines": sorted(sale_vat, key=itemgetter(0)),
				"total_base": sum([v[4] for v in sale_vat if v[4] > 0]),
				"total_tax": sum([v[5] for v in sale_vat if v[5] > 0])
			})
			taxes.append({
				"title": "IMPUESTO AL VALOR AGREGADO",
				"lines": sorted(vat, key=itemgetter(0)),
				"total_base": sum([v[4] for v in vat if v[4] > 0]),
				"total_tax": sum([v[5] for v in vat if v[5] > 0])
			})
			taxes.append({
				"title": "NOTAS DE CRÉDITO Y DEBITO",
				"lines": sorted(nc, key=itemgetter(0)),
				"total_base": sum([v[4] for v in nc if v[4] > 0]),
				"total_tax": sum([v[5] for v in nc if v[5] > 0])
			})
			taxes.append({
				"title": "RETENCIÓN EN LA FUENTE DE IVA",
				"lines": sorted(wh_vat, key=itemgetter(0)),
				"total_base": sum([v[4] for v in wh_vat if v[4] > 0]),
				"total_tax": sum([v[5] for v in wh_vat if v[5] > 0])
			})
			taxes.append({
				"title": "RETENCIONES APLICADAS A LA EMPRESA",
				"lines": sorted(sales, key=itemgetter(0)),
				"total_base": sum([v[4] for v in sales if v[4] > 0]),
				"total_tax": sum([v[5] for v in sales if v[5] > 0])
			})
			sheet = book.add_sheet("104")
			taxes.append({
				"title": "RETENCIÓN EN LA FUENTE DEL IMPUESTO A LA RENTA",
				"lines": sorted(wh_ir, key=itemgetter(0)),
				"total_base": sum([v[4] for v in wh_ir if v[4] > 0]),
				"total_tax": sum([v[5] for v in wh_ir if v[5] > 0])
			})
			buf = StringIO.StringIO()
			book.save(buf)
			out = base64.encodestring(buf.getvalue())
			buf.close()
			return {
				"type": "ir.actions.act_url",
				"url": "/web/content?model=%s&download=True&field=xml_file&id=%s&filename=%s"
				       % (self._inherit, self.id, "Impuestos.xlsx"),
				"target": "new",
			}

	def print_xls(self):
		def evalobj(obj, field):
			for attr in field.split("."):
				if hasattr(obj, attr):
					obj = getattr(obj, attr)
				else:
					break
			return obj

		self.ensure_one()
		book = Workbook()
		formtaxes = {}
		FIELDS = [
			(u"Fecha", "fecha", "std"),
			(u"Asiento", "asiento", "std"),
			(u"Documento", "documento", "std"),
			(u"Contribuyente", "tax_invoice_id.invoice_id.partner_id.name", "std"),
			(u"R.U.C.", "tax_invoice_id.invoice_id.partner_id.vat", "std"),
			(u"No. Retención", "tax_invoice_id.ret_id.name", "std"),
			(u"B. Imponible", "b_imponible", "num"),
			(u"Porcentaje", "porcentaje", "%"),
			(u"Valor", "valor", "num"),
			(u"Estado", "estado", "std")
		]
		FIELDS_RES = [
			(u"Tipo", "name", "std"),
			(u"Total B. Imponible", "b_total", "num"),
			(u"Total Valor", "v_total", "num"),
			(u"Movimientos", "lineas_ids", "std")
		]
		STYLES = {
			"std": style(),
			"bold": style(True, size=12),
			"title": style(True, font_color="white", color="periwinkle", align="center"),
			"%": style(format="0.00%"),
			"num": style(format="[$$-300A]#,##0.00;[$$-300A]-#,##0.00", align="right"),
			"numbold": style(True, format="[$$-300A]#,##0.00;[$$-300A]-#,##0.00", align="right")
		}
		for tax in self.get_taxes():
			sheet = book.add_sheet(formulario and str(formulario) or "Des")
			row = 5
			notes = []
			for tax in taxes:
				notes = [i for i in tax.lineas_ids if i.type in ("out_refund", "in_refund")]
				sheet.write(row, 0, "Impuesto: %s" % tax.name, STYLES["bold"])
				for col, field in enumerate(FIELDS, 0):
					sheet.write(row + 1, col, field[0], STYLES["title"])
				for aux, detail in enumerate(tax.lineas_ids, 0):
					for col, (field, attr, sty) in enumerate(FIELDS, 0):
						sheet.write(aux + row + 2, col, evalobj(detail, attr) or "", STYLES[sty])
				row += len(tax.lineas_ids) + 3
				if notes:
					sheet.write(row, 0, "Impuesto: Notas de Credito %s" % tax.name, STYLES["bold"])
					for col, field in enumerate(FIELDS, 0):
						sheet.write(row + 1, col, field[0], STYLES["title"])
					for aux, note in enumerate(notes, 0):
						for col, (field, attr, sty) in enumerate(FIELDS, 0):
							sheet.write(aux + row + 2, col, evalobj(note, attr) or "", STYLES[sty])
					row += len(notes) + 3
			# =======================================================================
			# Resumen Tributario
			sheet.write(row, 0, "RESUMEN TRIBUTARIO", STYLES["bold"])
			for col, field in enumerate(FIELDS_RES, 0):
				sheet.write(row + 2, col, field[0], STYLES["title"])
			row += 3
			for tax in taxes:
				name = ustr(tax.name)
				notes = [
					i for i in
					tax.lineas_ids if
					i.move_type in ("out_refund", "in_refund")
				]
				invoices = [
					i for i in tax.lineas_ids
					if i.move_type not in ("out_refund", "in_refund")
				]
				if notes:
					b_imponible = str(sum([n.b_imponible for n in notes]))
					valor = str(sum([n.valor for n in notes]))
					rec = "(%s Registros)" % str(len(notes))
					sheet.write(row, 0, "Notas de credito:"+ name or "", STYLES[sty])
					sheet.write(row, 1, b_imponible or "", STYLES[sty])
					sheet.write(row, 2, valor or "", STYLES[sty])
					sheet.write(row, 3, rec or "", STYLES[sty])
					row += 1
				if invoices:
					b_imponible = str(sum([n.b_imponible for n in invoices]))
					valor = str(sum([n.valor for n in invoices]))
					rec = "(%s Registros)" % str(len(invoices))
					sheet.write(row, 0, name or "", STYLES[sty])
					sheet.write(row, 1, b_imponible or "", STYLES[sty])
					sheet.write(row, 2, valor or "", STYLES[sty])
					sheet.write(row, 3, rec or "", STYLES[sty])
					row += 1
			row += 3
		buf = StringIO.StringIO()
		book.save(buf)
		out = base64.encodestring(buf.getvalue())
		buf.close()


		book.save(f_out)
		f_out.flush()
		self.export_pcr_file = base64.b64encode(open(f_out.name, "rb").read())
		self.export_pcr_filename = "Reporte de Pruebas PCR.xls"
		f_out.close()
		return {
			"type": "ir.actions.act_url",
			"url": "/web/content?model=%s&download=True&field=xml_file&id=%s&filename=%s"
			       % (self._inherit, self.id, "Impuestos.xlsx"),
			"target": "new",
		}

	# def action_print(self):
	# 	""" Prints Tax Report"""
	# 	report = self.env.ref("l10n_ec_withholding.account_tax_report")
	# 	return report.report_action(self)
