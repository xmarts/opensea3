# -*- coding: utf-8 -*-
import base64
from io import StringIO

import os
from os import path
import time
import itertools

from jinja2 import Environment, FileSystemLoader

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


from . import utils
from ..xades.sri import DocumentXML


class AccountWithholding(models.Model):
    _name = "account.withholding"
    _inherit = ["account.withholding", "account.edocument"]

    def _info_withdrawing(self, wh):
        """ Generar tag de retención """

        co = wh.company_id
        pa = wh.partner_id
        infoCompRetencion = {
            "fechaEmision": wh.date.strftime("%d/%m/%Y"),
            "dirEstablecimiento": "{}, {}".format(co.street, co.street2),
            "contribuyenteEspecial": co.taxpayer_code,
            "obligadoContabilidad": co.is_force_keep_accounting,
            "tipoIdentificacionSujetoRetenido": partner.l10n_latam_identification_type_id.code,  # noqa
            "razonSocialSujetoRetenido": pa.name,
            "identificacionSujetoRetenido": pa.vat,
            "periodoFiscal": wh.date.strftime("%m/%Y"),
        }
        return infoCompRetencion

    def _impuestos(self, wh):
        """ Obtiene detalle de impuestos
        :param withholding: record(account.withholding)
        :return:
        """

        def get_codigo_retencion(linea):
            """escoge ret iva / ret ir"""
            if linea.tax_id.tax_group_id.l10n_ec_type in (
                    "wh_vat", "wh_vat_services", "wh_vat_assets",
            ):
                return utils.tabla21[str(abs(int(line.tax_id.amount)))]
            else:
                code = linea.code
                return code

        impuestos = []
        baseretvat = 0
        for line in wh.tax_ids:
            if line.tax_id.tax_group_id.l10n_ec_type in (
                    "wh_vat", "wh_vat_services",
                    "wh_vat_assets", "wh_income_tax"
            ):
                baseretvat = line.base
            else:
                baseretvat = (line.base)
            k = get_codigo_retencion(line)
            impuesto = {
                "codigo": utils.tabla20[line.tax_id.tax_group_id.l10n_ec_type],
                "codigoRetencion": get_codigo_retencion(line),
                "baseImponible": "%.2f" % (baseretvat),
                "porcentajeRetener": "{:.2f}".format(abs(line.tax_id.amount)),
                "valorRetenido": "%.2f" % (abs(line.amount)),
                "codDocSustento": wh.move_id.support_id.code,
                "numDocSustento": wh.move_id.l10n_latam_document_number.replace("-",""),
                "fechaEmisionDocSustento": time.strftime("%d/%m/%Y", time.strptime(str(wh.move_id.invoice_date), "%Y-%m-%d"))  # noqa
            }
            impuestos.append(impuesto)
        return {"impuestos": impuestos}

    def render_document(self, doc, access_key, emission_code):
        """ Renders withholding XML

        :param document:
        :param access_key:
        :param emission_code:
        :return:
        """
        tmpl_path = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(tmpl_path))
        ewithdrawing_tmpl = env.get_template("ewithdrawing.xml")
        data = {}
        data.update(self._info_tributaria(doc, access_key, emission_code))
        data.update(self._info_withdrawing(doc))
        data.update(self._impuestos(doc))
        edocument = ewithdrawing_tmpl.render(data)
        return edocument

    def action_generate_ewithholding(self):
        """ Genera retención SRI """

        for wh in self:
            self.check_date(wh.date)
           # self.check_before_sent()
            access_key, emission_code = self._get_codes("account.withholding")
            ewithdrawing = self.render_document(wh, access_key, emission_code)
            inv_xml = DocumentXML(ewithdrawing, "withdrawing")
            if not inv_xml.validate_xml():
               raise ValidationError("Not Valid Schema")
            xades = self.env["l10n.ec.sri.key"].search([
                   ("company_id", "=", self.company_id.id)
            ])
            x_path = "/tmp/"
            if not path.exists(x_path):
                os.mkdir(x_path)
            to_sign_file = open(x_path+"RETENCION_SRI_"+self.name+".xml", "w")
            to_sign_file.write(ewithdrawing)
            to_sign_file.close()
            signed_document = xades.action_sign(to_sign_file)
            ok, errores = inv_xml.send_receipt(signed_document)
            if not ok:
                raise ValidationError(errores)
            sri_auth = self.env["l10n.ec.sri.authorization"].create({
		        "sri_authorization_code": access_key,
		        "sri_create_date": self.write_date,
		        "l10n_latam_document_type_id": self.l10n_latam_document_type_id.id,
		        "env_service": self.company_id.env_service,
		        "res_id": self.id,
		        "res_model": self._name,
	        })
            self.write({"sri_authorization_id": sri_auth.id})
            auth, m = inv_xml.request_authorization(access_key)
            if not auth:
                msg = " ".join(list(itertools.chain(*m)))
                raise ValidationError(msg)
            auth_einvoice = self.render_authorized_edocument(auth)
            self._update_document(auth, [access_key, emission_code])
            buf = StringIO()
            buf.write(auth_einvoice)
            xfile = base64.b64encode(buf.getvalue().encode())
            attachment = self.env["ir.attachment"].create({
                "name": "{}.xml".format(access_key),
                "datas": xfile,
                "res_model": self._name,
                "res_id": wh.id
            })

    def action_withholding_send(self):
        """ Open a window to compose an email, with the edi withholding template
            message loaded with electronic withholding data on pdf and xml.
        """
        return self.action_document_send("l10n_ec_einvoice.email_template_ewithholding")
