# Copyright 2017-2020 ForgeFlow, S.L.
# Copyright 2021 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class StockRule(models.Model):
    _inherit = "stock.rule"

    auto_create_group = fields.Boolean(
        string="Auto-create Reference",
        help="Give every procurement run through this rule a reference of its "
        "own, so its moves are not grouped with the ones already in progress.",
    )

    @api.model
    def _get_rule(self, product_id, location_id, values):
        # Odoo 18 and earlier carried this override on procurement.group, a
        # model Odoo 19 removed: _get_rule now lives on stock.rule.
        rule = super()._get_rule(product_id, location_id, values)
        # Without a planned date the call comes from outside a procurement run.
        if rule and rule.auto_create_group and values.get("date_planned"):
            values["reference_ids"] = rule._get_auto_stock_reference(product_id)
        return rule

    def _get_auto_stock_reference(self, product):
        return self.env["stock.reference"].create(
            self._prepare_auto_stock_reference_data(product)
        )

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super()._push_prepare_move_copy_values(move_to_copy, new_date)
        if self.auto_create_group:
            reference = self._get_auto_stock_reference(move_to_copy.product_id)
            new_move_vals["reference_ids"] = [Command.set(reference.ids)]
        return new_move_vals

    def _prepare_auto_stock_reference_data(self, product):
        name = (
            self.env["ir.sequence"].next_by_code("procurement.auto.create.group")
            or False
        )
        if not name:
            raise UserError(_("No sequence defined for the automatic reference."))
        # stock.reference holds a name and links to documents. The partner the
        # procurement group used to carry has no counterpart on it.
        return {"name": name}
