# Implementation Debt Kill List and Hardening Ladder

Date de controle: `25 mars 2026`

## Purpose

SwissBuilding is ambitious enough that implementation debt can quietly become a
strategic drag.

This pack defines what debt matters most and how to kill it in the right order.

## Rule

Kill debt that:

- slows validation loops
- weakens canonical truth
- creates duplicated concepts
- makes features harder to trust

Ignore debt that is only cosmetic if it does not affect those.

## Debt ladder

### Level 1 - truth debt

Examples:

- duplicated concepts
- mismatched identity semantics
- stale source-to-product mappings
- hidden conflicting read models

Why first:

- this poisons everything above it

### Level 2 - execution debt

Examples:

- slow validation loops
- poor test targeting
- unreliable seeds
- fragile imports

Why second:

- this slows every wave

### Level 3 - UX clarity debt

Examples:

- same meaning rendered differently
- missing next-action emphasis
- hidden caveats

Why third:

- this reduces perceived product quality and habit formation

### Level 4 - expansion debt

Examples:

- unclear integration boundaries
- weak pack contracts
- poor release exposure semantics

Why fourth:

- this slows safe growth

## Current highest-payoff debt themes

- auth regression and validation-noise debt
- duplicated or implicit workflow semantics
- hidden uncertainty instead of explicit review
- stale index or brief lookup drift
- identity-resolution ambiguity

## Product rule

Do not label every annoyance as debt.

Strategic debt is the debt that compounds against:

- truth
- speed
- trust
- adoption

## Acceptance

This pack is succeeding when future cleanup work is prioritized by strategic
effect instead of by random irritation.
