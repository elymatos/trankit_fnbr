# Issue tracker: GitHub

Issues and specifications live in GitHub Issues for `elymatos/trankit_fnbr`.
Use the `gh` CLI for all operations.

## Conventions

- Create: `gh issue create --title "..." --body "..."`
- Read: `gh issue view <number> --comments`
- List: `gh issue list`
- Comment: `gh issue comment <number> --body "..."`
- Label: `gh issue edit <number> --add-label "..."`
- Close: `gh issue close <number> --comment "..."`

Infer the repository from `git remote -v`.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Skill terminology

- “Publish to the issue tracker” means create a GitHub issue.
- “Fetch the relevant ticket” means run `gh issue view <number> --comments`.
