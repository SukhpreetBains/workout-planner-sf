// Tiered edge-weight model. Each edge carries a `type` string; the weight
// determines how strongly it pulls two nodes into the same feature cluster.
//
// STRONG (3) — structural / ownership: these almost always mean "same feature".
// MEDIUM (2) — meaningful references that often, but not always, stay in-feature.
// WEAK   (1) — cross-cutting references that should not, on their own, merge features.

export const STRONG = 3
export const MEDIUM = 2
export const WEAK = 1

// Edge types produced by the parsers / API mapper, mapped to a tier.
export const EDGE_WEIGHTS = {
  // --- containment / ownership (STRONG) ---
  'object-owns-field': STRONG,
  'object-owns-recordtype': STRONG,
  'object-owns-validationrule': STRONG,
  'trigger-on-object': STRONG,
  'trigger-uses-handler': STRONG,
  'flow-on-object': STRONG,
  'flexipage-for-object': STRONG,
  'flexipage-hosts-component': STRONG,

  // --- meaningful references (MEDIUM) ---
  'lookup': MEDIUM,
  'apex-references-apex': MEDIUM,
  'flow-calls-subflow': MEDIUM,
  'flow-calls-apex': MEDIUM,
  'quickaction-targets': MEDIUM,
  'layout-uses-action': MEDIUM,
  'psg-includes-permset': MEDIUM,

  // --- cross-cutting access / refs (WEAK) ---
  'permset-grants-object': WEAK,
  'permset-grants-field': WEAK,
  'permset-grants-apex': WEAK,
  'permset-grants-tab': WEAK,
  'references-label': WEAK,
  'references-staticresource': WEAK,
  'references-custommetadata': WEAK,

  // --- API backbone (unknown semantics) ---
  // MetadataComponentDependency edges we couldn't classify keep a MEDIUM default.
  'api-dependency': MEDIUM,
}

export function weightFor(edgeType) {
  return EDGE_WEIGHTS[edgeType] ?? MEDIUM
}
