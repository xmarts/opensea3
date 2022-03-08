# -*- coding: utf-8 -*-

import requests


tipoDocumento = {
    '01': '01',
    '04': '04',
	'03': '03',
	'05': '05',
    '06': '06',
    '07': '07',
    '18': '01',
}

# tipoIdentificacion = {
#     'RUC': '04',
#     #'cedula': '05',
#     'Ced': '05',
#     'pasaporte': '06',
#     'venta_consumidor_final': '07',
#     'identificacion_exterior': '08',
#     'placa': '09',
# }

codigoImpuesto = {
    'vat12': '2',
    'vat14': '3',
    'zero_vat': '0',
    'ice': '3',
    'other': '5'
}

#CODIGO PORCENTAJE IMPUESTOS
tabla16 = {
    'vat12': '2',
	'vat14': '2',
    'zero_vat': '2',
	'exempt_vat': '2',
	'not_charged_vat': '2',
	'ice': '3',
    'irbpnr': '5'
}

#CODIGO PORCENTAJE IVA
tabla17 = {
    '0': '0',
    '12': '2',
    '14': '3',
    'not_charget_vat': '6',
    'excempt_vat': '7'
}

tabla20 = {
    'wh_income_tax': '1',
    'wh_vat': '2',
    'others': '6'
}

tabla21 = {
	#RENTA
	'2': '327',
	'3': '328',
	#IVA
    '10': '9',
    '20': '10',
    '30': '1',
    '50': '11',
    '70': '2',
    '100': '3'
}

codigoImpuestoRetencion = {
    'wh_income_tax': '1',
	'wh_vat': '2',
	'ice': '3',
    'isd': '6',
}

tarifaImpuesto = {
    'zero_vat': '0',
    'vat12': '2',
    'not_charget_vat': '6',
    'other': '7',
}

MSG_SCHEMA_INVALID = u"El sistema generó el XML pero"
" el comprobante electrónico no pasa la validación XSD del SRI."

SITE_BASE_TEST = 'https://celcer.sri.gob.ec/'
SITE_BASE_PROD = 'https://cel.sri.gob.ec/'
WS_TEST_RECEIV = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'  # noqa
WS_TEST_AUTH = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'  # noqa
#WS_TEST_RECEIV = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl'  # noqa
#WS_TEST_AUTH = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl'  # noqa
WS_RECEIV = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'  # noqa
WS_AUTH = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'  # noqa


def check_service(env, url):
	flag = False
	if env == 'test':
		URL = url
	else:
		URL = url

	for i in [1, 2, 3]:
		try:
			res = requests.head(URL, timeout=3)
			flag = True
		except requests.exceptions.RequestException:
			return flag, False
	return flag, res