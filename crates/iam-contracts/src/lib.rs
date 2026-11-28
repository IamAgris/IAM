//! Versioned, language-neutral message envelopes for IAM's Python–Rust boundary.
//!
//! This crate deliberately contains **no business logic**. It defines only the
//! transport envelope described in `docs/IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md`
//! §5: a stable schema name, an explicit version and an opaque JSON payload.
//! Payload shapes remain owned by the existing Python contracts in
//! `backend/app/services/ai_research/` and `sdk/PROTOCOL.md`.

use serde::{Deserialize, Serialize};

/// Version of the envelope format itself.
///
/// This is distinct from the `version` carried by each [`Envelope`], which
/// describes the version of that envelope's `schema`.
pub const ENVELOPE_VERSION: u32 = 1;

/// A versioned message that can cross the Python–Rust boundary.
///
/// The `schema` and `version` fields are mandatory so that a receiver can
/// reject an unknown contract before interpreting `payload`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Envelope {
    /// Stable, language-neutral identifier for the payload contract.
    pub schema: String,

    /// Version of the named schema. Never inferred or defaulted.
    pub version: u32,

    /// Payload data, left opaque so this crate cannot duplicate business logic.
    pub payload: serde_json::Value,
}

impl Envelope {
    /// Creates an envelope for an explicitly named and versioned schema.
    pub fn new(schema: impl Into<String>, version: u32, payload: serde_json::Value) -> Self {
        Self {
            schema: schema.into(),
            version,
            payload,
        }
    }

    /// Returns `true` when this envelope declares the given schema name.
    pub fn supports_schema(&self, schema: &str) -> bool {
        self.schema == schema
    }

    /// Serializes the envelope to JSON.
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }

    /// Deserializes an envelope from JSON.
    ///
    /// Missing `schema` or `version` fields are rejected rather than defaulted.
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn sample() -> Envelope {
        Envelope::new(
            "iam.research.result.v1",
            1,
            json!({"experiment_id": "01JTEST0000000000000000000", "ok": true}),
        )
    }

    #[test]
    fn round_trip_preserves_every_field() {
        let original = sample();
        let decoded = Envelope::from_json(&original.to_json().expect("serialize")).expect("parse");
        assert_eq!(decoded, original);
        assert_eq!(decoded.version, 1);
    }

    #[test]
    fn schema_is_explicit_and_checkable() {
        let envelope = sample();
        assert!(envelope.supports_schema("iam.research.result.v1"));
        assert!(!envelope.supports_schema("iam.research.job.v1"));
    }

    #[test]
    fn malformed_json_is_rejected() {
        assert!(Envelope::from_json("{").is_err());
    }

    #[test]
    fn missing_version_is_rejected() {
        let json = r#"{"schema":"iam.research.result.v1","payload":{}}"#;
        assert!(Envelope::from_json(json).is_err());
    }
}
