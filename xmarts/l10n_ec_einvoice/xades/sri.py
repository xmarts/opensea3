# -*- coding: utf-8 -*-

import base64
import logging
import os
from io import StringIO

from lxml import etree
from lxml.etree import fromstring, DocumentInvalid

try:
   from suds.client import Client
except ImportError:
    logging.getLogger("xades.sri").info("Instalar libreria suds-jurko")

from ..models import utils
from .xades import CheckDigit

from odoo.exceptions import ValidationError

SCHEMAS = {
    "out_invoice": "schemas/factura.xsd",
    "out_refund": "schemas/nota_credito.xsd",
    "withdrawing": "schemas/retencion.xsd",
    "delivery": "schemas/guia_remision.xsd",
    "in_refund": "schemas/nota_debito.xsd",
    "liq_purchase": "schemas/liquidacion_compra.xsd"
}


class DatosTributarios:
    def __init__(self,claveAcceso='',numeroAutorizacion='',FechaAutorizacion='',Estado='',Ambiente=''):
        self.claveAcceso=claveAcceso
        self.numeroAutorizacion=numeroAutorizacion
        self.FechaAutorizacion=FechaAutorizacion
        self.Estado=Estado
        self.Ambiente=Ambiente


class DocumentXML(object):
    _schema = False
    document = False

    @classmethod
    def __init__(cls, document, type_document="out_invoice"):
        """
        document: XML representation. Hace el parser xml xsd
        type: determinate schema
        """

        parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
        cls.document = fromstring(document.encode("utf-8"), parser=parser)
        cls.type_document = type_document
        cls._schema = SCHEMAS[cls.type_document]
        cls.signed_document = False
        cls.logger = logging.getLogger("xades.sri")

    @classmethod
    def validate_xml(self):
        """
        Validar esquema XML. Se imprime en formato
        """
        self.logger.info("Validacion de esquema")
        self.logger.debug(etree.tostring(self.document, pretty_print=True))
        file_path = os.path.join(os.path.dirname(__file__), self._schema)
        schema_file = open(file_path)
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        try:
            xmlschema.assertValid(self.document)
            return True
        except DocumentInvalid:
            raise ValidationError(xmlschema.error_log)

    @classmethod
    def consulta_factura(cls, clave_acceso):
        if len(clave_acceso)!=49:
            raise ('Clave de acceso no es valida')

        flag = False
        sri = SriService()
        datosTributarios = DatosTributarios()
        messages = []
        client = Client(SriService.get_active_ws()[1])
        result = client.service.autorizacionComprobante(clave_acceso)
        return flag, datosTributarios

    @classmethod
    def send_receipt(cls, document):
        """
            Método que envia el XML al Werbservice del SRI
        :param document: str
        :return: Boolean
        """
        cls.logger.info('Enviando documento para recepcion SRI')
        buffer_xml = base64.b64encode(bytes(document, 'utf-8')).decode('ascii')
        buffer_xml = buffer_xml.replace('\n', '')
        sri = SriService()
        url = sri.get_ws_test()
        if not utils.check_service('prueba', url):
            # TODO: implementar modo offline
            raise 'Error SRI'('Servicio SRI no disponible.')

        client = Client(SriService.get_active_ws()[0])
        result = client.service.validarComprobante(buffer_xml)
        cls.logger.info('Estado de respuesta documento: %s' % result.estado)
        errores = []
        if result.estado == 'RECIBIDA':
            return True, errores
        else:
            for comp in result.comprobantes:
                for m in comp[1][0].mensajes:
                    rs = [m[1][0].tipo, m[1][0].mensaje]
                    rs.append(getattr(m[1][0], 'informacionAdicional', ''))
                    errores.append(' '.join(rs))
            cls.logger.error(errores)
            return False, ', '.join(errores)

    def request_authorization(self, access_key):
        messages = []
        client = Client(SriService.get_active_ws()[1])
        result = client.service.autorizacionComprobante(access_key)
        autorizacion = result.autorizaciones[0][0]
        mensajes = autorizacion.mensajes and autorizacion.mensajes[0] or []
        for m in mensajes:
            self.logger.error('{0} {1} {2}'.format(
                m.identificador, m.mensaje, m.tipo, m.informacionAdicional)
            )
            messages.append([m.identificador, m.mensaje,
                             m.tipo, m.informacionAdicional])
        if not autorizacion.estado == 'AUTORIZADO':
            return False, messages
        return autorizacion, messages

    # def consulta_factura(self, clave_acceso):
    #     if len(clave_acceso) != 49:
    #         raise ('Clave de acceso no es valida')
    #     flag = False
    #     datosTributarios = DatosTributarios()
    #     messages = []
    #     client = Client(SriService.get_active_ws()[1])
    #     result = client.service.autorizacionComprobante(clave_acceso)
    #     return flag, datosTributarios


class SriService(object):

    __AMBIENTE_PRUEBA = "1"
    __AMBIENTE_PROD = "2"
    __ACTIVE_ENV = False
    # revisar el utils
    __WS_TEST_RECEIV = "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl"
    __WS_TEST_AUTH = "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"  # noqa

    #  __WS_TEST_RECEIV = "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl"  # noqa
 #   __WS_TEST_AUTH = "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl"  # noqa
    __WS_RECEIV = "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl"  # noqa
    __WS_AUTH = "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"  # noqa

    __WS_TESTING = (__WS_TEST_RECEIV, __WS_TEST_AUTH)
    __WS_PROD = (__WS_RECEIV, __WS_AUTH)

    _WSDL = {
        __AMBIENTE_PRUEBA: __WS_TESTING,
        __AMBIENTE_PROD: __WS_PROD
    }
    __WS_ACTIVE = __WS_TESTING

    @classmethod
    def set_active_env(cls, env_service):
        if env_service == cls.__AMBIENTE_PRUEBA:
            cls.__ACTIVE_ENV = cls.__AMBIENTE_PRUEBA
        else:
            cls.__ACTIVE_ENV = cls.__AMBIENTE_PROD
        cls.__WS_ACTIVE = cls._WSDL[cls.__ACTIVE_ENV]

    @classmethod
    def get_active_env(cls):
        return cls.__ACTIVE_ENV

    @classmethod
    def get_env_test(cls):
        return cls.__AMBIENTE_PRUEBA

    @classmethod
    def get_env_prod(cls):
        return cls.__AMBIENTE_PROD

    @classmethod
    def get_ws_test(cls):
        return cls.__WS_TEST_RECEIV, cls.__WS_TEST_AUTH

    @classmethod
    def get_ws_prod(cls):
        return cls.__WS_RECEIV, cls.__WS_AUTH

    @classmethod
    def get_active_ws(cls):
        return cls.__WS_ACTIVE

    @classmethod
    def create_access_key(cls, values):
        """ Entra clave acceso en crudo, intercala
        el ambiente y obtiene el digito verificador
        values: tuple ([], [])
        """
        env = cls.get_active_env()
        dato = "".join(values[0] + [env] + values[1])
        modulo = CheckDigit.compute_mod11(dato)
        access_key = "".join([dato, str(modulo)])
        return access_key
