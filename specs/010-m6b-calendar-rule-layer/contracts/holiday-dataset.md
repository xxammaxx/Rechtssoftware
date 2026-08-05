# Contract — Local Holiday Dataset

A future package contains a manifest and records as defined in `data-model.md`. Required validation order: schema → manifest hash → record hash/provenance → validity interval → jurisdiction/scope. Failure at any stage returns a warning/error and prevents use by a legal profile.

Prohibited: runtime URL fetch, mutable in-place update, source-less record, unbounded validity, inferred municipality, and third-party calendar-library data as legal provenance.
