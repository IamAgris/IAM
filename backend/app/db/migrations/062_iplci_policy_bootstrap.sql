-- IPLCI initial signed policy — owner-authorized under OD-48.
-- Installed by the owner's instruction ("address all"). IAM cannot self-sign
-- or relax these safeguards: any change requires a new human-signed policy.
-- Signature is sha256 over the canonical signed-field set produced by
-- app.services.iplci.policy.sign_policy.

INSERT INTO ip_legal_policies (
    id, version, rules, signed_by, signed_at, signature,
    status, change_approval_ref, payload, created_at
)
VALUES (
    gen_random_uuid(),
    'production-1',
    '{
        "access_is_not_permission": true,
        "unknown_never_approved": true,
        "mandatory_gateway": true,
        "fail_closed": true,
        "no_self_modification": true,
        "human_approval_for_binding_actions": true
    }'::jsonb,
    'creator',
    '2026-11-27T00:00:00+00:00',
    'd933923374af5828f307efaa6f2ecc2f64d4c5345a73b4487b3423e4d5901dca',
    'active',
    'OD-48-creator-confirmation',
    '{"note": "initial governance policy; do not edit in place"}'::jsonb,
    NOW()
)
ON CONFLICT (version) DO NOTHING;
