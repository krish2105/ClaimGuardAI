---
doc_id: fraud_waste_abuse_definitions
plan_type: All
category: coding_policy
effective_date: 2026-01-01
---

# Fraud, Waste, and Abuse Definitions

*This document is the primary reference retrieved by the Coding Agent
(filtered to `category=coding_policy`) when evaluating coding-integrity
flags. Definitions are written for adjuster and model use, not as legal
text.*

## Clause CG-FWA-001: Upcoding

Upcoding is the practice of billing for a higher-complexity or higher-cost
procedure or visit level than the one actually performed or clinically
supported by the documentation. Indicators include a billed amount that
significantly exceeds the typical cost band for the documented diagnosis
severity, or a procedure code inconsistent with the visit duration/setting
implied by the claim.

## Clause CG-FWA-002: Unbundling

Unbundling is billing separately for individual components of a procedure
that should be billed together under a single, more comprehensive procedure
code. Indicators include multiple same-day CPT codes from the same provider
for the same patient that together approximate a single bundled procedure's
scope, submitted as separate line items to inflate total reimbursement.

## Clause CG-FWA-003: Phantom Billing

Phantom billing is billing for services, tests, or supplies that were never
actually provided to the patient. A common pattern is multiple same-day
claims from the same provider and patient for procedures spanning
clinically unrelated specialties or body systems, which is inconsistent with
a single coherent care episode and should be treated as a strong fraud
indicator by the Fraud Scoring Agent.

## Clause CG-FWA-004: Diagnosis-Procedure Mismatch

A diagnosis-procedure mismatch occurs when the billed CPT procedure code has
no plausible clinical relationship to the accompanying ICD-10 diagnosis code
(for example, a dermatology procedure billed against an orthopedic
diagnosis). This is distinct from upcoding, which involves a correct
diagnosis-procedure category paired with an inflated cost or complexity
level.

## Clause CG-FWA-005: Provider Risk Signals

Providers with a rising 30-day claim frequency substantially above their
historical baseline, or with a documented `flagged_history_count` greater
than zero in the provider registry, should be treated as a contributing risk
factor by the Fraud Scoring Agent, though it must never be the sole basis
for an automatic denial without a corroborating coding or documentation flag.
