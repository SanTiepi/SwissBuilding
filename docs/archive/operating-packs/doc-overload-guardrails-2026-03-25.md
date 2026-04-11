# Doc Overload Guardrails

Date de controle: `25 mars 2026`

## Purpose

The pack system is now large enough that documentation itself can become a
source of drag.

This document defines when to add a new pack and when to stop.

## Rule

Do not add a new pack unless it does at least one of:

- compresses many decisions into one clearer artifact
- creates a directly launchable brief
- removes ambiguity that would otherwise slow execution
- adds a reusable control surface for future waves

## Prefer updating over adding when possible

Prefer:

- updating `claude-now-priority-stack`
- updating `claude-operating-pack-registry`
- updating `claude-wave-brief-kit`

Instead of creating a new standalone pack for a minor refinement.

## Signs of overload

- too many packs say nearly the same thing
- the next move is harder to choose, not easier
- a new pack adds categorization but no action
- reading cost rises faster than execution value

## Preferred response to overload

- compress
- merge
- raise one clearer stack
- reduce browse paths

## Acceptance

This guardrail is succeeding when the doc system keeps making execution easier,
not heavier.
