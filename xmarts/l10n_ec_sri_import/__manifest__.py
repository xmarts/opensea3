# -*- coding: utf-8 -*-
{
    'name': 'Invoice import',
    'version': '14.0.1.0.0',
    'category': 'Localization',
	'summary': """Imports SRI TXT and XMl documents""",
	'description': """ """,
    'author': 'Xmarts[elymar.alfaro@xmarts.com].',
    'depends': ['l10n_ec_einvoice'],
    'data': [
        'security/ir.model.access.csv',
	    'views/l10n_ec_import_document_line_view.xml',
	    'views/l10n_ec_import_document_view.xml',
	    'views/l10n_ec_import_file_line_view.xml',
    ],
}
