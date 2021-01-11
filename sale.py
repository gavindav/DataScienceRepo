# (C) Copyright IBM Corp. 2020
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""SaleOrder."""

from odoo import api, fields, models
from odoo.tools.config import config
import re


class SaleOrder(models.Model):
    """SaleOrder."""

    _inherit = 'sale.order'

    case_number = fields.Char('case_number', required=False)

    def _get_ddb_service_types(self):
        return self.env['delivery.carrier']._get_ddb_service_types()

    ddb_service_type = fields.Selection(
        _get_ddb_service_types, string="DDB Service Type")

    @api.onchange('carrier_id')
    def _onchange_carrier_id(self):
        """Return the element value."""
        orders = self.env['sale.order'].sudo().search(
            [('package_delivery_group', '=', self.package_delivery_group)])
        delivery_type = self.carrier_id.delivery_type
        for order in orders:
            order.carrier_id = self.carrier_id
            if hasattr(
                    self.carrier_id, delivery_type + "_default_service_type"):
                expr = "order." + delivery_type + \
                    "_service_type = self.carrier_id." + \
                    delivery_type + "_default_service_type"
                exec(expr)
            order.ibmorder_data.deliverymethod = self.carrier_id.name

    def generate_next_case_number_in_sequence(self, base_initialisation):
        ddbcase_obj = self.env['ibmddb.case_number'].with_user(2).create({'ordno': self.name, })
        case_num = ddbcase_obj.id
        while case_num < base_initialisation:
            ddbcase_obj.unlink()
            ddbcase_obj = self.env['ibmddb.case_number'].with_user(2).create({'ordno': self.name, })
            case_num = ddbcase_obj.id
        return case_num

    def int2base36(self, x, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
        """Convert an integer to its string representation to base 36."""
        val = ''
        while x > 0:
            x, idx = divmod(x, 36)
            val = alphabet[idx] + val
        return "0" * (5 - len(val)) + val

    def get_ddb_case_number(self):
        """Return the element value."""
        # format is 76ZSWAaaaaa00
        # initialise from 00000 so sumber is from 76ZSWA0000000 to
        # 76ZSWAZZZZZ00
        ddbprefix = config.get("ddbprefix")
        ddb_base_initialisation = config.get("ddb_base_initialisation")
        if ddb_base_initialisation and re.match("^[0-9]*$", ddb_base_initialisation.strip()):
            ddb_base_initialisation = int(ddb_base_initialisation.strip(), 36)
        else:
            ddb_base_initialisation = 0    # 10 = 'AXXXXX', 11='BXXXXX'
        if ddbprefix and re.match("^[0-9]*$", ddbprefix.strip()):
            ddbprefix = int(ddbprefix.strip())
        else:
            ddbprefix = 10    # 10 = 'AXXXXX', 11='BXXXXX'
        foundation = 36 * ddbprefix * 36 * 36 * 36 * 36
        if self.case_number:
            return self.case_number
        else:
            case_number_prefix = "76ZSW"
            case_num = self.generate_next_case_number_in_sequence(ddb_base_initialisation)
            case_num = self.int2base36(case_num + foundation)
            case_number_suffix = "00"
            self.case_number = case_number_prefix + case_num + \
                case_number_suffix
            pdg_sale_objects = self.env['sale.order'].sudo().search(
                [('package_delivery_group', '=', self.package_delivery_group)])
            for pdg_so in pdg_sale_objects:
                pdg_so.case_number = case_number_prefix + case_num + \
                    case_number_suffix
            return self.case_number
