# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_outgoing_incoming_moves(self, strict=True):
        """Conta entrambi i movimenti prodotti dalla regola MTS+MTO.

        Con ``strict=False`` Odoo 19 non somma i movimenti uscenti per ubicazione di
        destinazione, ma per **regola scatenante**, e ne registra una sola per
        magazzino::

            for move in sorted_moves:
                if move.warehouse_id.id not in seen_wh_ids and move.rule_id:
                    triggering_rule_ids.append(move.rule_id.id)
                    seen_wh_ids.add(move.warehouse_id.id)

        L'euristica presuppone che una riga d'ordine generi un solo movimento verso il
        cliente per magazzino. ``split_procurement`` rompe il presupposto: a giacenza
        parziale genera **due** movimenti, uno con la sottoregola MTS e uno con la
        sottoregola MTO. Il primo entra in ``triggering_rule_ids``, il secondo no e non
        viene contato.

        La conseguenza non e' cosmetica. ``sale_stock._action_launch_stock_rule``
        confronta la quantita' cosi' contata con quella della riga, la trova inferiore e
        lancia un secondo approvvigionamento per la differenza: nasce un movimento
        fantasma e soprattutto un ordine di produzione per la quantita' **intera**
        invece che per il solo residuo. Misurato su un ordine da 2 pezzi con 1 a
        magazzino: tre movimenti verso il cliente e una produzione da 2.

        Per queste righe si torna al conteggio per ubicazione di destinazione
        (``strict=True``), che e' quello che faceva la 17.0 e che somma correttamente
        entrambi i movimenti. Le altre righe non sono toccate.

        Limite noto: ``strict=True`` ignora i movimenti intermedi delle consegne a piu'
        fasi. Con ``ship_only`` non cambia nulla; su ``pick_ship`` o ``pick_pack_ship``
        andrebbe invece esteso ``triggering_rule_ids`` con le sottoregole, non forzato
        ``strict``.
        """
        if not strict and self._has_mts_mto_moves():
            strict = True
        return super()._get_outgoing_incoming_moves(strict=strict)

    def _has_mts_mto_moves(self):
        """Vero se i movimenti della riga vengono dalle sottoregole di una MTS+MTO."""
        rules = self.move_ids.rule_id
        if not rules:
            return False
        split_rules = self.env["stock.rule"].search(
            [("action", "=", "split_procurement")]
        )
        sub_rules = split_rules.mts_rule_id | split_rules.mto_rule_id
        return bool(set(rules.ids) & set(sub_rules.ids))
