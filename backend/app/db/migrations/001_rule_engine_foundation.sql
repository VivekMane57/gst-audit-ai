-- =============================================================
-- Migration: 001_rule_engine_foundation
-- Project:   GST-AUDIT-AI
-- Purpose:   DB-driven rule engine foundation
-- Run on:    Supabase SQL editor (production) or psql
-- Safe:      All tables are new — zero existing tables touched
-- Timezone:  All timestamps UTC. App converts to IST on display.
-- =============================================================

-- ── Extensions (idempotent) ───────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- future: rule_code fuzzy search


-- =============================================================
-- 1. law_catalog
--    Source of truth for all GST act/section references.
--    Referenced by compliance_rules.law_code (soft FK — not enforced
--    at DB level to allow partial seeding and forward refs).
-- =============================================================
CREATE TABLE IF NOT EXISTS law_catalog (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    law_code          TEXT        NOT NULL UNIQUE,   -- "CGST_16_2_AA", "CGST_74"
    act_name          TEXT        NOT NULL,           -- "CGST Act 2017"
    section           TEXT        NOT NULL,           -- "Section 16(2)(aa)"
    short_text        TEXT        NOT NULL,           -- One-line legal summary
    official_source_url TEXT,                         -- cbic.gov.in link
    reviewed_on       DATE,                           -- Last human-reviewed date
    is_active         BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE law_catalog IS
    'GST act sections catalog. Referenced by compliance_rules.';
COMMENT ON COLUMN law_catalog.law_code IS
    'Stable internal code. Format: ACT_SECTION_SUBSECTION. Never rename after seeding.';


-- =============================================================
-- 2. compliance_rules
--    Core rule registry. Engine reads only is_active=TRUE rows
--    within effective_from/effective_to window.
--
--    condition_config stores a PORTABLE condition tree (not SQL,
--    not Python). The evaluator in rule_engine_service.py walks it.
--    penalty_formula_config stores typed formula params.
--    Both are JSONB — indexed for performance.
-- =============================================================
CREATE TABLE IF NOT EXISTS compliance_rules (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    rule_code            TEXT        NOT NULL UNIQUE,
    -- Format: CATEGORY_SHORTNAME_VN  e.g. ITC_GSTR2B_MISSING_V1
    -- Never reuse a retired code. Increment version suffix instead.

    title                TEXT        NOT NULL,
    description          TEXT        NOT NULL,

    -- Taxonomy
    category             TEXT        NOT NULL,
    -- Allowed: itc | invoicing | gstin | reconciliation | hsn |
    --          filing | fraud | classification | tax_computation | sector
    -- Validated at application layer (enum), not DB constraint
    -- (allows adding categories without migration)

    severity             TEXT        NOT NULL DEFAULT 'MEDIUM',
    -- Allowed: CRITICAL | HIGH | MEDIUM | LOW

    -- Condition tree — evaluated by rule_engine_service.py
    -- Example:
    -- {
    --   "type": "all",
    --   "conditions": [
    --     {"field": "gstr2b_present", "operator": "equals", "value": false},
    --     {"field": "itc_claimed",    "operator": "gt",     "value": 0}
    --   ]
    -- }
    condition_type       TEXT        NOT NULL DEFAULT 'all',
    -- Top-level combinator: all | any | not | always_flag
    -- 'always_flag' = no condition eval, flag every invoice (used for
    -- custom sector checks where detection is external)

    condition_config     JSONB       NOT NULL DEFAULT '{}',
    -- Full condition tree. Empty object = engine skips eval (use
    -- condition_type = 'always_flag' explicitly instead)

    -- Law reference
    law_code             TEXT,
    -- Soft reference to law_catalog.law_code
    -- NULL allowed: rule can exist before law entry is seeded

    plain_explanation    TEXT,
    -- Non-legalese explanation for CA firm dashboard display

    -- Penalty config
    penalty_formula_type TEXT        NOT NULL DEFAULT 'no_penalty',
    -- Allowed: fixed_amount | percentage_of_amount |
    --          tax_plus_interest_percent | late_fee_per_day |
    --          no_penalty | custom_exposure_note
    -- Handler lives in penalty_engine_service.py

    penalty_formula_config JSONB     NOT NULL DEFAULT '{}',
    -- Formula params. Shape depends on penalty_formula_type:
    -- fixed_amount:              {"amount": 10000, "currency": "INR"}
    -- percentage_of_amount:      {"rate": 0.18, "cap": 500000}
    -- tax_plus_interest_percent: {"tax_rate": 0.18, "interest_rate": 0.18,
    --                             "interest_period_days": 365}
    -- late_fee_per_day:          {"amount_per_day": 100, "max_days": 180}
    -- custom_exposure_note:      {"note": "Exposure depends on..."}
    -- no_penalty:                {}

    -- Risk engine
    notice_risk_weight   FLOAT       NOT NULL DEFAULT 0.0,
    -- 0.0–35.0 contribution to notice probability score.
    -- Maps to notice_simulator.ISSUE_WEIGHTS[type]["weight"]
    notice_risk_max      FLOAT       NOT NULL DEFAULT 10.0,
    -- Cap on this rule's contribution (regardless of severity mult)

    -- Versioning
    is_active            BOOLEAN     NOT NULL DEFAULT TRUE,
    version              INTEGER     NOT NULL DEFAULT 1,
    -- Increment on every meaningful rule change. Old version row
    -- should be set is_active=FALSE, new row inserted.
    effective_from       DATE,
    -- NULL = always effective from the beginning
    effective_to         DATE,
    -- NULL = currently in effect / no sunset date

    -- Audit trail
    created_by           TEXT,        -- clerk_id of creator (NULL for system-seeded)
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE compliance_rules IS
    'DB-driven GST compliance rule registry. Engine reads this table dynamically.';
COMMENT ON COLUMN compliance_rules.rule_code IS
    'Stable immutable code. Maps to IssueType enum values in models/issue.py.';
COMMENT ON COLUMN compliance_rules.condition_config IS
    'Portable JSON condition tree. Evaluated by rule_engine_service.py evaluator.';
COMMENT ON COLUMN compliance_rules.notice_risk_weight IS
    'Base weight contributing to notice probability. Max capped by notice_risk_max.';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_compliance_rules_category
    ON compliance_rules(category) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_compliance_rules_active_effective
    ON compliance_rules(is_active, effective_from, effective_to);

CREATE INDEX IF NOT EXISTS idx_compliance_rules_rule_code
    ON compliance_rules(rule_code);


-- =============================================================
-- 3. rule_fix_steps
--    Fix steps for each rule, in all 3 languages.
--    step_order controls display sequence.
--    Separate from compliance_rules to allow multi-step fixes
--    and independent updates without versioning the parent rule.
-- =============================================================
CREATE TABLE IF NOT EXISTS rule_fix_steps (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code    TEXT        NOT NULL,
    -- References compliance_rules.rule_code (soft FK)
    -- Soft because: steps can be pre-seeded before rule is active,
    -- and we don't want cascade delete to wipe steps on rule deactivate

    step_order   INTEGER     NOT NULL DEFAULT 1,
    step_text_en TEXT        NOT NULL,
    step_text_hi TEXT        NOT NULL DEFAULT '',
    step_text_mr TEXT        NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (rule_code, step_order)
    -- Prevents duplicate step ordering per rule
);

COMMENT ON TABLE rule_fix_steps IS
    'Ordered fix steps per compliance rule. Multi-language.';

CREATE INDEX IF NOT EXISTS idx_rule_fix_steps_rule_code
    ON rule_fix_steps(rule_code, step_order);


-- =============================================================
-- 4. risk_thresholds
--    Controls how notice probability % maps to risk labels.
--    is_default=TRUE row is the system default.
--    tenant_id=NULL means platform-wide default.
--    Future: add tenant_id for firm-specific thresholds.
--
--    Invariant: low_max < medium_max < high_max <= critical_min
--    Enforced at application layer, not DB constraint
--    (simpler than multi-column check constraint).
-- =============================================================
CREATE TABLE IF NOT EXISTS risk_thresholds (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_name TEXT        NOT NULL UNIQUE,
    -- e.g. "default" | "conservative" | "lenient"
    -- "default" profile_name is the system default

    -- Probability bands (0–100 integer scale)
    low_max      INTEGER     NOT NULL DEFAULT 24,
    medium_max   INTEGER     NOT NULL DEFAULT 44,
    high_max     INTEGER     NOT NULL DEFAULT 69,
    critical_min INTEGER     NOT NULL DEFAULT 70,
    -- Interpretation:
    -- 0–low_max       → LOW
    -- low_max+1–medium_max → MEDIUM
    -- medium_max+1–high_max → HIGH
    -- critical_min+   → VERY_HIGH

    is_default   BOOLEAN     NOT NULL DEFAULT FALSE,
    -- Only ONE row should have is_default=TRUE.
    -- Partial unique index enforces this:
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enforce single default profile
CREATE UNIQUE INDEX IF NOT EXISTS idx_risk_thresholds_single_default
    ON risk_thresholds(is_default) WHERE is_default = TRUE;

COMMENT ON TABLE risk_thresholds IS
    'Notice probability → risk label threshold config. One default row required.';


-- =============================================================
-- 5. penalty_configs
--    Global penalty config overrides. Allows updating penalty
--    rates (e.g. interest rate changes per Finance Act) without
--    touching individual rules.
--    Rules reference these via penalty_formula_type.
-- =============================================================
CREATE TABLE IF NOT EXISTS penalty_configs (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key    TEXT        NOT NULL UNIQUE,
    -- e.g. "gst_interest_rate" | "late_fee_per_day_cgst" | "fraud_penalty_multiplier"

    config_value  JSONB       NOT NULL,
    -- {"rate": 0.18} or {"amount": 200} or {"multiplier": 2.0}

    description   TEXT,
    effective_from DATE,
    effective_to   DATE,
    is_active      BOOLEAN    NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE penalty_configs IS
    'Global penalty rate configs. Updated per Finance Act without rule-level changes.';

CREATE INDEX IF NOT EXISTS idx_penalty_configs_active
    ON penalty_configs(config_key) WHERE is_active = TRUE;


-- =============================================================
-- 6. tenant_rule_overrides  [STUB — empty, no data yet]
--    Future: CA firm-level rule customizations.
--    Stub exists now so future migration is additive, not structural.
--    Schema is intentionally minimal — expand when needed.
-- =============================================================
CREATE TABLE IF NOT EXISTS tenant_rule_overrides (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    TEXT        NOT NULL,   -- ca_id (clerk_id of CA firm)
    rule_code    TEXT        NOT NULL,
    -- What the tenant can override:
    is_active    BOOLEAN,               -- NULL = inherit platform default
    severity     TEXT,                  -- NULL = inherit
    notice_risk_weight FLOAT,           -- NULL = inherit
    override_reason TEXT,               -- Required note explaining why
    created_by   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (tenant_id, rule_code)
);

COMMENT ON TABLE tenant_rule_overrides IS
    'STUB: Future per-CA-firm rule customizations. Empty in Phase 1.';


-- =============================================================
-- 7. rule_audit_log
--    Immutable log of all rule/law/threshold changes.
--    Non-negotiable for a compliance SaaS.
--    Never delete rows from this table.
-- =============================================================
CREATE TABLE IF NOT EXISTS rule_audit_log (
    id           BIGSERIAL   PRIMARY KEY,
    -- BIGSERIAL not UUID — append-only, sequential scan is fine

    entity_type  TEXT        NOT NULL,
    -- 'compliance_rule' | 'law_catalog' | 'risk_threshold' |
    -- 'rule_fix_step' | 'penalty_config'

    entity_id    TEXT        NOT NULL,
    -- UUID of the changed row (stored as TEXT for flexibility)

    action       TEXT        NOT NULL,
    -- 'created' | 'updated' | 'deactivated' | 'reactivated'

    changed_by   TEXT,       -- clerk_id of actor (NULL for system/seed)
    changed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    before_state JSONB,      -- NULL for 'created' action
    after_state  JSONB,      -- NULL for hard deletes (we don't hard delete)

    change_note  TEXT        -- Optional human comment on why
);

COMMENT ON TABLE rule_audit_log IS
    'Immutable audit trail for all rule engine config changes. Never delete rows.';

CREATE INDEX IF NOT EXISTS idx_rule_audit_log_entity
    ON rule_audit_log(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_rule_audit_log_changed_at
    ON rule_audit_log(changed_at DESC);


-- =============================================================
-- 8. Auto-updated updated_at trigger function
-- =============================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger to all mutable tables
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'law_catalog',
        'compliance_rules',
        'rule_fix_steps',
        'risk_thresholds',
        'penalty_configs',
        'tenant_rule_overrides'
    ]
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS set_updated_at ON %I;
             CREATE TRIGGER set_updated_at
             BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();',
            t, t
        );
    END LOOP;
END;
$$;


-- =============================================================
-- 9. Row Level Security (RLS)
--    IMPORTANT: Supabase enables RLS by default on new tables.
--    These tables are INTERNAL (admin + backend service key only).
--    Service role key bypasses RLS — safe for backend use.
--    Anon/authenticated roles get no access.
-- =============================================================
ALTER TABLE law_catalog           ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_rules      ENABLE ROW LEVEL SECURITY;
ALTER TABLE rule_fix_steps        ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_thresholds       ENABLE ROW LEVEL SECURITY;
ALTER TABLE penalty_configs       ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_rule_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE rule_audit_log        ENABLE ROW LEVEL SECURITY;

-- Service role (backend) has full access. No anon/user policies needed.
-- Admin panel (future) will use service key — same access.
-- NOTE: If you add a custom admin role later, add policies here.


-- =============================================================
-- 10. Seed: Default risk threshold (required — app fails without it)
-- =============================================================
INSERT INTO risk_thresholds (profile_name, low_max, medium_max, high_max, critical_min, is_default)
VALUES ('default', 24, 44, 69, 70, TRUE)
ON CONFLICT (profile_name) DO NOTHING;


-- =============================================================
-- 11. Seed: Global penalty configs (maps to PENALTY_MULTIPLIERS)
-- =============================================================
INSERT INTO penalty_configs (config_key, config_value, description, is_active) VALUES
('gst_interest_rate',           '{"rate": 0.18}',  'GST interest rate p.a. — Section 50 CGST Act', TRUE),
('fraud_penalty_multiplier',    '{"multiplier": 2.0}', 'Fraud/circular transaction penalty — 200% of ITC', TRUE),
('late_fee_per_day_cgst',       '{"amount": 100}', 'Late fee per day CGST — Section 47', TRUE),
('late_fee_per_day_sgst',       '{"amount": 100}', 'Late fee per day SGST — Section 47', TRUE),
('itc_penalty_rate',            '{"rate": 1.0}',   'ITC wrongly availed penalty — 100% of ITC amount', TRUE),
('tax_mismatch_interest_rate',  '{"rate": 0.18}',  'Interest on wrong tax type cases', TRUE)
ON CONFLICT (config_key) DO NOTHING;


-- =============================================================
-- VERIFICATION QUERY — Run after migration to confirm
-- =============================================================
-- SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name)))
-- FROM information_schema.tables
-- WHERE table_schema = 'public'
--   AND table_name IN (
--       'law_catalog', 'compliance_rules', 'rule_fix_steps',
--       'risk_thresholds', 'penalty_configs', 'tenant_rule_overrides', 'rule_audit_log'
--   )
-- ORDER BY table_name;