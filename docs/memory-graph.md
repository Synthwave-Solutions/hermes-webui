# Memory graph sources

The Memory explorer reads the selected bank's legacy `triples`, BEAM `facts`
and `memoria_kg` assertions. A bank can contain modern facts while its legacy
table is empty. Graph, triples, search, session detail, daily digest and graph
counts use the same normalized sources. Missing timestamps and confidence stay
unknown; records keep source-qualified IDs and provenance. Assertions from
different sessions remain distinct evidence. `graph_edges` links memory IDs and
is deliberately not presented as entity assertions.

The adapter is `api/memdash_graph.py`; it leaves pinned vendor files unchanged.
It uses only the existing authorized, read-only, deadline-bound bank connection.
It does not migrate data or change bank ownership. The standalone dashboard can
install the same adapter into its DashboardStore after applying its connection
guard. No extraction API or credentials are required for displaying stored facts.

Regression: `./scripts/test.sh -q tests/test_memdash_graph_sources.py` uses a
synthetic bank with an empty legacy table and populated modern tables, including
bank isolation, parameterized search, bounds, legacy coexistence and no writes.
