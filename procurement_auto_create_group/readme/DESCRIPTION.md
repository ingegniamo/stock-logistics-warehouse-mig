This module gives every procurement run a stock reference of its own, so
its moves are never mixed in a transfer with moves from other runs.

The transfers resulting from the run then contain only the stock moves
created in that run.

Odoo 19 note: the model `procurement.group` no longer exists. Odoo
replaced it with `stock.reference`, a name plus links to the documents
involved, and the moves carry `reference_ids` instead of `group_id`. This
module creates one of those references. The partner the procurement group
used to carry has no counterpart on a reference, so it is no longer set.
