import os

from datetime import datetime
from jinja2 import Environment, FileSystemLoader

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from . import utils
from ..xades.sri import SriService, DocumentXML


class AccountEdocument(models.AbstractModel):
    """ Modelo para la generación de documentos
    electrónicos en Ecuador:

    DOCUMENTOS ELECTRÓNICOS
    -* Facturas (01)
    -* Liquidación de Compra de Bienes y Prestación de Servicios (03)
    -* Nota de Crédito (04)
    -* Nota de Débito (05)
    -* Guía de Remisión (06)
    -* Comprobante de Retención (07)

    SUJETOS RETENIDOS

    -* RUC (04)
    -* CÉDULA (05)
    -* PASAPORTE (06)
    -* VENTA A CONSUMIDOR FINAL (07)
    -* IDENTIFICACIÓN DEL EXTERIOR (08)

    ESTADOS DE DOCUMENTO ELECTRÓNICO
    -* En procesamiento (PPR)
    -* Autorizado (AUT)
    -* No autorizado (NAT)
    """
    _name = "account.edocument"
    _description = "Model for Ecuador's Electronic Documents"
    _FIELDS = {
        "account.move": "name",
        "account.withholding": "name",
        "account.remission.guide": "name",
    }
    AUTH_TEMP = {
        "account.move": "authorized_einvoice.xml",
        "account.withholding": "authorized_withdrawing.xml",
        "account.remission.guide": "authorized_eremission.xml"
    }
    SriServiceObj = SriService()

    sri_authorization_id = fields.Many2one(
        "l10n.ec.sri.authorization",
        string="SRI Authorization",
        copy=False
    )
    clave_acceso = fields.Char(
        string="Clave de Acceso",
        related="sri_authorization_id.sri_authorization_code",
        copy=False
    )
    numero_autorizacion = fields.Char(
        string="Número de Autorización",
        related="sri_authorization_id.sri_authorization_code",
        copy=False
    )
    estado_autorizacion = fields.Char(
        string="Estado de Autorización",
        copy=False
    )
    fecha_autorizacion = fields.Datetime(
        string="Fecha Autorización",
    #    related="sri_authorization_id.sri_create_date",
        copy=False
    )
    ambiente = fields.Char(
        string="Ambiente",
    #    related="sri_authorization_id.env_service",
        copy=False
    )
    autorizado_sri = fields.Boolean(
        string="¿Autorizado SRI?",
        copy=False
    )
    emission_code = fields.Char(
        string="Tipo de Emisión",
        size=1,
        #related="sri_authorization_id",
        copy=False
    )
    sent = fields.Boolean(string="Enviado?")
    to_cancel = fields.Boolean(string="To Cancel")

    def _get_secuencial(self):
        return getattr(self, self._FIELDS[self._name])[8:]

    def _info_tributaria(self, doc, access_key, emission_code):
        """ Arma la estructura de la cabecera infotributaria de cada XML
        :param doc: record(account.move)
        :param access_key: str(clave_acceso)
        :param emission_code:
        :return: dict()
        """
        co = doc.company_id
        infoTributaria = {
            "ambiente": co.env_service,
            "tipoEmision": emission_code,
            "razonSocial": co.name,
            "nombreComercial": co.name,
            "ruc": co.vat,
            "claveAcceso": access_key,
            "codDoc": utils.tipoDocumento[doc.l10n_latam_document_type_id.code],
            "estab": doc.l10n_ec_emission_point_id.name,
            "ptoEmi": doc.l10n_ec_emission_point_id.entity_id.name,
            "secuencial": access_key[30:39],
            "dirMatriz": co.street or "",
        }
        if co.regime:
            infoTributaria.update({
                "regimenMicroempresas": "CONTRIBUYENTE RÉGIMEN MICROEMPRESAS",
            })
        if co.agent:
            infoTributaria.update({"agenteRetencion": co.agent_text})
        if co.rimpe_regime:
            infoTributaria.update({
                "contribuyenteRimpe": "CONTRIBUYENTE RÉGIMEN RIMPE",
            })
        return infoTributaria

    def get_code(self):
        """ Obtiene el siguiente secuencial para la clave de acceso """
        code = self.env["ir.sequence"].next_by_code("edocuments.code")
        if not code:
            raise ValidationError("You need to set a sequence for e-documents")
        return code

    def _get_access_key(self, name):
        """ Generates the acces key for each document with
        49 digits:

        -* Fecha de emisión: ddmmaaaa (8)
        -* Tipo de Comprobante: (2)
        -* Número d RUC: 1234567890001 (13)
        -* Tipo de Ambiente: 1(Pruebas) o 2(Producción) (1)
        -* Serie: 001001 (6)
        -* Número del comprobante( secuencial): 000000001 (9)
        -* Código Numérico: Código de seguridad a potestad del emisor (8)
        -* Tipo de Emisión: (1)
        -* Dígito Verificador (módulo 11): Se aplica sobre los
                                       48 digits anteiores1 o 0 (1)
        """
        if name == "account.move":
            doc = self.move_type
            ld = str(self.invoice_date).split("-")
            numero = getattr(self, "l10n_latam_document_number").replace("-", "")
            codigo_numero = self.get_code()
            vals = {
                "out_invoice": "01",
                "out_refund": "04",
                "in_invoice": "03",
                "in_refund": "05",
              }
            a = vals.get(doc)
        elif name == "account.withholding":
            doc = self.withholding_type
            ld = str(self.date).split("-")
            numero = getattr(self, "name").replace("-", "")
            codigo_numero = self.get_code()
            if doc == "in_invoice":
                a = "07"
        ld.reverse()
        fecha = "".join(ld)
        tcomp = utils.tipoDocumento[a]
        ruc = self.company_id.vat
        tipo_emision = self.company_id.emission_code
        access_key = (
            [fecha, tcomp, ruc],
            [numero, codigo_numero, tipo_emision]
            )
        return access_key

    def _get_codes(self, name="account.move"):
        """ Generates acces key and emission code """
        ak_temp = self._get_access_key(name)
        self.SriServiceObj.set_active_env(self.env.user.company_id.env_service)
        access_key = self.SriServiceObj.create_access_key(ak_temp)
        emission_code = self.company_id.emission_code
        return access_key, emission_code

    def check_before_sent(self):
        """
        Verifica si la factura anterior esta
        posteada y si se envió al sri
        """
        MESSAGE_SEQUENCIAL = " ".join([
            u"Los comprobantes electrónicos deberán ser",
            u"enviados al SRI para su autorización en orden cronológico",
            "y secuencial. Por favor enviar primero el",
            " comprobante inmediatamente anterior."])
        FIELD = {
            "account.move": "l10n_latam_document_number",
            "account.withholding": "name"
        }
        number = getattr(self, FIELD[self._name])
        sql = " ".join([
            "SELECT autorizado_sri, %s FROM %s" % (FIELD[self._name], self._table),  # noqa
            "WHERE state='posted' AND %s < '%s'" % (FIELD[self._name], number),  # noqa
            self._name == "account.move" and "AND move_type='out_invoice'",
            "ORDER BY %s DESC LIMIT 1" % FIELD[self._name]
        ])
        self.env.cr.execute(sql)
        res = self.env.cr.fetchone()
        if not res:
            return True
        auth, number = res
        if auth is None and number:
            raise ValidationError(MESSAGE_SEQUENCIAL)
        return True

    @staticmethod
    def check_date(invoice_date):
        """ Valida que el envío del comprobante electrónico
        se realice dentro de las 24 horas posteriores a su emisión """

        LIMIT_TO_SEND = 5
        MESSAGE_TIME_LIMIT = u" ".join([
            u"Los comprobantes electrónicos deben",
            u"enviarse con máximo 24h desde su emisión."]
        )
        dt = datetime.strptime(str(invoice_date), "%Y-%m-%d")
        days = (datetime.now() - dt).days
        if days > LIMIT_TO_SEND:
            raise ValidationError(MESSAGE_TIME_LIMIT)

    def _update_document(self, auth, codes):
        """ Updates sent document with
        answer values from SRI """

        fecha = auth.fechaAutorizacion.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.write({
            "numero_autorizacion": auth.numeroAutorizacion,
            "estado_autorizacion": auth.estado,
            "ambiente": auth.ambiente,
            "fecha_autorizacion": fecha,
            "autorizado_sri": True,
            "clave_acceso": codes[0],
            "emission_code": codes[1]
        })

    def render_authorized_edocument(self, autorizacion):
        """ Renders authorized XML document"""
        tmpl_path = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(tmpl_path))
        edocument_tmpl = env.get_template(self.AUTH_TEMP[self._name])
        auth_xml = {
            "estado": autorizacion.estado,
            "numeroAutorizacion": autorizacion.numeroAutorizacion,
            "ambiente": autorizacion.ambiente,
            "fechaAutorizacion": str(autorizacion.fechaAutorizacion),
            "comprobante": autorizacion.comprobante
        }
        auth_document = edocument_tmpl.render(auth_xml)
        return auth_document

    def render_document(self, document, access_key, emission_code):
        pass

    def action_document_send(self, template):
        """ Open a window to compose an email, with the edi invoice template
            message loaded with electronic invoice data on pdf and xml.
        """
        self.ensure_one()
        template_id = self.env.ref(template, raise_if_not_found=False)
        attachment_id = self.env["ir.attachment"].create({
            "name": "{}.xml".format(self.clave_acceso),
            "datas": self.sri_authorization_id.xml_file
        })
        template_id.update({"attachment_ids": [(6, 0, [attachment_id.id])]})
        lang = False
        if template_id:
            lang = template_id._render_lang(self.ids)[self.id]
        if not lang:
            lang = self.get_lang(self.env).code
        compose_form = self.env.ref(
	        "mail.email_compose_message_wizard_form",
            raise_if_not_found=False
        )
        ctx = dict(
            default_model=self._name,
            default_res_id=self.id,
            default_res_model=self._name,
            default_use_template=bool(template_id),
            default_template_id=template_id and template_id.id or False,
            default_composition_mode="comment",
            mark_invoice_as_sent=True,
            custom_layout="mail.mail_notification_paynow",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True
        )
        return {
            "name": _("Send Document"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form.id, "form")],
            "view_id": compose_form.id,
            "target": "new",
            "context": ctx,
        }
