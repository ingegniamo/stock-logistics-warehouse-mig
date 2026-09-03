# Copyright 2017-2020 ForgeFlow, S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestProcurementAutoCreateGroup(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        # Odoo 19 removed procurement.group: references replace it and
        # stock.rule carries both the Procurement tuple and run().
        cls.reference_obj = cls.env["stock.reference"]
        cls.rule_obj = cls.env["stock.rule"]
        cls.route_obj = cls.env["stock.route"]
        cls.move_obj = cls.env["stock.move"]
        cls.picking_obj = cls.env["stock.picking"]
        cls.product_obj = cls.env["product.product"]

        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.location = cls.env.ref("stock.stock_location_stock")
        cls.company_id = cls.env.ref("base.main_company")
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        # Odoo 19 no longer ships stock.stock_location_components: the packing
        # zone is the internal location left that is not WH/Stock itself.
        cls.loc_components = cls.env.ref("stock.location_pack_zone")
        picking_type_id = cls.env.ref("stock.picking_type_internal").id

        cls.partner = cls.env["res.partner"].create({"name": "Partner"})

        # Create rules and routes:
        pull_push_route_auto = cls.route_obj.create({"name": "Auto Create Group"})
        cls.pull_push_rule_auto = cls.rule_obj.create(
            {
                "name": "rule with autocreate",
                "route_id": pull_push_route_auto.id,
                "auto_create_group": True,
                "action": "pull_push",
                "warehouse_id": cls.warehouse.id,
                "picking_type_id": picking_type_id,
                "location_dest_id": cls.location.id,
                "location_src_id": cls.loc_components.id,
                "partner_address_id": cls.partner.id,
            }
        )
        pull_push_route_no_auto = cls.route_obj.create(
            {"name": "Not Auto Create Group"}
        )
        cls.rule_obj.create(
            {
                "name": "rule with no autocreate",
                "route_id": pull_push_route_no_auto.id,
                "auto_create_group": False,
                "action": "pull_push",
                "warehouse_id": cls.warehouse.id,
                "picking_type_id": picking_type_id,
                "location_dest_id": cls.location.id,
                "location_src_id": cls.loc_components.id,
            }
        )
        push_route_auto = cls.route_obj.create({"name": "Auto Create Group"})
        cls.push_rule_auto = cls.rule_obj.create(
            {
                "name": "route_auto",
                "location_src_id": cls.location.id,
                "location_dest_id": cls.loc_components.id,
                "route_id": push_route_auto.id,
                "auto_create_group": True,
                "auto": "manual",
                "picking_type_id": picking_type_id,
                "warehouse_id": cls.warehouse.id,
                "company_id": cls.company_id.id,
                "action": "push",
            }
        )
        push_route_no_auto = cls.route_obj.create({"name": "Not Auto Create Group"})
        cls.rule_obj.create(
            {
                "name": "route_no_auto",
                "location_src_id": cls.location.id,
                "location_dest_id": cls.loc_components.id,
                "route_id": push_route_no_auto.id,
                "auto_create_group": False,
                "auto": "manual",
                "picking_type_id": picking_type_id,
                "warehouse_id": cls.warehouse.id,
                "company_id": cls.company_id.id,
                "action": "push",
            }
        )

        # Prepare products:
        cls.prod_auto_pull_push = cls.product_obj.create(
            {
                "name": "Test Product 1",
                "is_storable": True,
                "route_ids": [(6, 0, [pull_push_route_auto.id])],
            }
        )
        cls.prod_no_auto_pull_push = cls.product_obj.create(
            {
                "name": "Test Product 2",
                "is_storable": True,
                "route_ids": [(6, 0, [pull_push_route_no_auto.id])],
            }
        )
        cls.prod_auto_push = cls.product_obj.create(
            {
                "name": "Test Product 3",
                "is_storable": True,
                "route_ids": [(6, 0, [push_route_auto.id])],
            }
        )
        cls.prod_no_auto_push = cls.product_obj.create(
            {
                "name": "Test Product 4",
                "is_storable": True,
                "route_ids": [(6, 0, [push_route_no_auto.id])],
            }
        )

        cls.reference = cls.reference_obj.create({"name": "SO0001"})

    @classmethod
    def _procure(cls, product):
        values = {
            "reference_ids": cls.reference,
        }
        cls.rule_obj.run(
            [
                cls.rule_obj.Procurement(
                    product,
                    5.0,
                    product.uom_id,
                    cls.location,
                    "TEST",
                    "odoo tests",
                    cls.env.company,
                    values,
                )
            ]
        )
        return True

    @classmethod
    def _push_trigger(cls, product):
        picking = cls.picking_obj.create(
            {
                "picking_type_id": cls.env.ref("stock.picking_type_in").id,
                "location_id": cls.supplier_location.id,
                "location_dest_id": cls.location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "date_deadline": "2099-06-01 18:00:00",
                            "date": "2099-06-01 18:00:00",
                            "product_uom": product.uom_id.id,
                            "product_uom_qty": 1.0,
                            "location_id": cls.supplier_location.id,
                            "location_dest_id": cls.location.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.move_ids.write({"quantity": 1.0})
        picking.button_validate()

    def test_01_pull_push_no_auto_create_reference(self):
        """The reference given to the run is the one that reaches the move."""
        move = self.move_obj.search(
            [("product_id", "=", self.prod_no_auto_pull_push.id)]
        )
        self.assertFalse(move)
        self._procure(self.prod_no_auto_pull_push)
        move = self.move_obj.search(
            [("product_id", "=", self.prod_no_auto_pull_push.id)]
        )
        self.assertTrue(move)
        self.assertEqual(
            move.reference_ids,
            self.reference,
            "No reference of its own should have been created.",
        )

    def test_02_pull_push_auto_create_reference(self):
        move = self.move_obj.search([("product_id", "=", self.prod_auto_pull_push.id)])
        self.assertFalse(move)
        self._procure(self.prod_auto_pull_push)
        move = self.move_obj.search([("product_id", "=", self.prod_auto_pull_push.id)])
        self.assertTrue(move)
        self.assertTrue(move.reference_ids, "Reference not assigned.")
        self.assertNotEqual(
            move.reference_ids,
            self.reference,
            "The rule should have replaced the reference with a new one.",
        )
        self.assertTrue(
            move.reference_ids.name.startswith("AUTO/"),
            "The reference should be named from the module sequence, got %r"
            % move.reference_ids.name,
        )

    def test_03_the_switch_stands_alone(self):
        """Odoo 19 removed group_propagation_option, which used to clear it."""
        self.assertTrue(self.push_rule_auto.auto_create_group)
        self.assertNotIn("group_propagation_option", self.rule_obj._fields)
        self.assertFalse(
            hasattr(self.rule_obj, "_onchange_group_propagation_option"),
            "The onchange guarded a field that no longer exists.",
        )

    def test_04_push_no_auto_create_reference(self):
        move = self.move_obj.search(
            [
                ("product_id", "=", self.prod_no_auto_push.id),
                ("location_dest_id", "=", self.loc_components.id),
            ]
        )
        self.assertFalse(move)
        self._push_trigger(self.prod_no_auto_push)
        move = self.move_obj.search(
            [
                ("product_id", "=", self.prod_no_auto_push.id),
                ("location_dest_id", "=", self.loc_components.id),
            ]
        )
        self.assertTrue(move)
        self.assertFalse(
            move.reference_ids, "No reference should have been assigned."
        )

    def test_05_push_auto_create_reference(self):
        move = self.move_obj.search(
            [
                ("product_id", "=", self.prod_auto_push.id),
                ("location_dest_id", "=", self.loc_components.id),
            ]
        )
        self.assertFalse(move)
        self._push_trigger(self.prod_auto_push)
        move = self.move_obj.search(
            [
                ("product_id", "=", self.prod_auto_push.id),
                ("location_dest_id", "=", self.loc_components.id),
            ]
        )
        self.assertTrue(move)
        self.assertTrue(move.reference_ids, "Reference not assigned.")
