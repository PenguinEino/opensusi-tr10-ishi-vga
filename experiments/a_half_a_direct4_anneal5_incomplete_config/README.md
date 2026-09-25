# Incomplete setup archive — not a candidate

The first `half_a_tight_rows.py prepare` call ran before the source seed had
produced `layout/placement.json`. It failed before writing a source manifest or
applying the tight row-width constraint. A subsequent solve also failed packing.

This directory preserves those intermediate files only. It has no approved
provenance manifest or routed result and is excluded from the A feasibility
comparison. The correctly prepared generation is `a_half_a_direct4_anneal5`;
its explicit repacking derivative is `a_half_a_direct4_repack5`.
