# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from os.path import join, dirname, realpath
from odoo import api, SUPERUSER_ID
import csv


def post_init_hook(cr, registry):
	env = api.Environment(cr, SUPERUSER_ID, {})

	if not env['edi.res.locality'].search_count([]):
		csv_path = join(dirname(realpath(__file__)), 'data', 'res.country.csv')
		vals_list = []
		with open(csv_path, 'r') as csv_file:
			for row in csv.DictReader(csv_file, delimiter='|', fieldnames=['id:id', 'l10n_ec_country_code']):
				country = env.ref(row['id:id'], raise_if_not_found=False)
				country.write({'l10n_ec_country_code':  row['l10n_ec_country_code']})

