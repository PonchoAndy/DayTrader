# Architecture Decision Records

Each file here records one decision: what we chose, why, and what it means for the project.
They're short, numbered, and never deleted. If a decision changes, we write a new record that
**supersedes** the old one and mark the old one as superseded.

## Index

| # | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-blizzard-api-as-primary-data-source.md) | Blizzard Game Data API as the primary data source | Accepted |
| [0003](0003-us-region-horde-primary-collect-all-houses.md) | US region, Horde primary, collect every auction house | Accepted |
| [0004](0004-github-issues-and-issue-deck-workflow.md) | GitHub issues as the work tracker, with the Issue Deck | Accepted |
| [0005](0005-hourly-collection-on-github-actions-with-object-storage.md) | Hourly collection on GitHub Actions, data in object storage | Proposed |

## Statuses

- **Proposed**: suggested, waiting for your OK. Reply on the linked issue or tell Claude.
- **Accepted**: decided. Build on it.
- **Superseded by NNNN**: replaced by a later record.
- **Rejected**: considered and turned down (kept so we don't revisit it by accident).

## Adding one

Copy [`template.md`](template.md) to the next number, e.g. `0006-short-title.md`, fill it in,
and add it to the index above. Link the issue where the decision was discussed.
