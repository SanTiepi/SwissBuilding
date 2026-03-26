# Passport Exchange Network Foundation Pack

Date de controle: `25 mars 2026`

## Purpose

Le `Passport Exchange Network` n'est pas un marketplace.

C'est la couche qui permet a des systemes et acteurs differents de:

- publier un pack
- consommer un pack
- savoir quelle version a ete acceptee
- garder une trace d'import, de rejet, de remplacement et de compatibilite

Cette fondation sert a faire de SwissBuilding un chemin d'echange, pas juste
une application locale.

## Core principle

Start with:

- versioned contracts
- publications
- imports
- receipts

Do not start with:

- public discovery network
- ecosystem billing
- multi-party marketplace complexity

## Minimum objects

### ExchangeContractVersion

Defines one supported exchange contract.

Minimum shape:

- `id`
- `contract_code`
- `version`
- `status`
- `audience_type`
- `payload_type`
- `schema_reference`
- `effective_from`
- `effective_to`
- `compatibility_notes`

### PassportPublication

Represents one outbound publication from SwissBuilding.

Minimum shape:

- `id`
- `building_id`
- `contract_version_id`
- `audience_type`
- `publication_type`
- `pack_id`
- `content_hash`
- `published_at`
- `published_by_org_id`
- `published_by_user_id`
- `delivery_state`

### PassportImportReceipt

Represents one inbound receipt from another system or actor.

Minimum shape:

- `id`
- `building_id`
- `source_system`
- `contract_code`
- `contract_version`
- `import_reference`
- `imported_at`
- `status`
- `content_hash`
- `matched_publication_id`
- `notes`

### ExchangeCapabilityProfile

Describes what a connected system or actor can send or receive.

Minimum shape:

- `id`
- `partner_code`
- `partner_type`
- `supported_contract_codes`
- `supported_versions`
- `supports_receipts`
- `supports_acknowledgements`
- `supports_delta_updates`

## Existing anchors to reuse

The network must extend:

- passport package
- transfer package
- diagnostic publication package
- `ProofDelivery`
- future `Authority Flow`

It must not create:

- a second passport model
- a second pack engine
- a second trust layer

## Product questions the network must answer

- what did we publish
- under which contract version
- who consumed it
- was it accepted or rejected
- which version is current
- can a downstream system trust the payload

## Build sequence

### E1

Stabilize local contract discipline:

- `contract_code`
- `version`
- `audience_type`
- `payload_type`

### E2

Add publication and import receipt traces:

- outbound publication object
- inbound receipt object
- current version versus superseded version

### E3

Only later add:

- partner capability profiles
- handshake validation
- delta or incremental updates
- cross-system compatibility negotiation

## Acceptance

The foundation is good when SwissBuilding can prove:

- which pack version was published
- under which contract
- what another system accepted
- which version remains the active shared truth
