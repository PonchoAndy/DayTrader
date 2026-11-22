# Architecture Decision Records

Each file here records one decision: what we chose, why, and what it means for the project.
They're short, numbered, and never deleted. If a decision changes, we write a new record that
**supersedes** the old one and mark the old one as superseded.

## Index

| # | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-blizzard-api-as-primary-data-source.md) | Blizzard Game Data API as the primary data source | Accepted |
| [0003](0003-us-region-horde-primary-collect-all-houses.md) | US region, Horde primary, collect every auction house | Accepted; region part superseded by 0009 |
| [0004](0004-github-issues-and-issue-deck-workflow.md) | GitHub issues as the work tracker, with the Issue Deck | Accepted |
| [0005](0005-hourly-collection-on-github-actions-with-object-storage.md) | Hourly collection on GitHub Actions, data in object storage | Partly accepted (storage, scheduler, language; dashboard proposed) |
| [0006](0006-private-repo-hourly-collector-on-github-actions.md) | Private repo; hourly Python collector on GitHub Actions | Accepted |
| [0007](0007-keep-hourly-summaries-three-months-then-review.md) | Keep hourly summaries 3 months, review their value | Accepted |
| [0008](0008-analysis-layer-daily-rollup-listing-flows-versioned-metrics.md) | Analysis layer: daily roll-up, listing flows, versioned metrics | Partly accepted (listing flows + extra trading and posting-behaviour measures); rest proposed |
| [0009](0009-collect-europe-in-the-same-hourly-run.md) | Collect Europe's auction data in the same hourly run | Accepted |
| [0010](0010-build-helper-agents-in-the-repo.md) | Build-helper agents live in the repo, hand off through saved documents | Accepted |
| [0011](0011-money-whole-copper-shown-as-four-decimal-gold.md) | Money is whole copper underneath; shown as gold with four decimals | Accepted |
| [0012](0012-home-house-114-ruleset-from-house-id.md) | Home house is 114 (US Normal Horde); the ruleset comes from the house ID | Accepted |
| [0013](0013-three-phases-of-use.md) | Three phases of use: playground, app, AH terminal | Accepted |
| [0014](0014-trading-day-starts-12-utc.md) | A trading day starts at 12:00 UTC (7am US Eastern in winter) | Accepted |
| [0015](0015-stockpile-ticker-live-from-page-database.md) | Stockpile Ticker updates itself: numbers hourly, Analyst briefings every 6 hours | Accepted |
| [0016](0016-claude-sessions-read-r2-directly.md) | Claude sessions read the R2 storage directly, read-only | Accepted |
| [0017](0017-backup-collect-run-at-35.md) | A backup collect run at :35 past each hour | Accepted |
| [0018](0018-item-classes-rare-items-and-vendor-floors.md) | Ammunition on its own, rare items as a separate class, vendor price as a floor marker | Accepted |
| [0019](0019-commit-often-review-then-merge.md) | Commit often, review every batch, then merge | Accepted |

## Statuses

- **Proposed**: suggested, waiting for your OK. Reply on the linked issue or tell Claude.
- **Accepted**: decided. Build on it.
- **Superseded by NNNN**: replaced by a later record.
- **Rejected**: considered and turned down (kept so we don't revisit it by accident).

## Adding one

Copy [`template.md`](template.md) to the next number, e.g. `0011-short-title.md`, fill it in,
and add it to the index above. Link the issue where the decision was discussed.
