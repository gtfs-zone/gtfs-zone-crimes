# Contributing to crimes.gtfs.zone

## Commit Message Guidelines

This project uses [Conventional Commits](https://www.conventionalcommits.org/) to automate versioning and changelog generation.

### Using Commitizen

Instead of `git commit`, use:

```bash
pnpm commit
```

This will prompt you to fill out the commit message following the conventional format. `git commit` also works, as long as the message is valid.

`cz` is the Python [Commitizen](https://commitizen-tools.github.io/commitizen/), not the npm package. Install it with:

```bash
pipx install commitizen
```

### Commit Message Format

Each commit message consists of a **type**, an optional **scope**, and a **subject**:

```
<type>(<scope>): <subject>
```

#### Types

- `feat`: A new feature (triggers minor version bump)
- `fix`: A bug fix (triggers patch version bump)
- `docs`: Documentation only changes
- `style`: Changes that don't affect the meaning of the code (white-space, formatting, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A performance improvement
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes that affect the build system or external dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files
- `revert`: Reverts a previous commit

#### Breaking Changes

Add `BREAKING CHANGE:` in the commit body or add `!` after the type/scope to trigger a major version bump:

```bash
feat!: remove support for old API
```

### Examples

```bash
feat(crimes): convict feeds with unreadable route colours
fix(supersonic): ignore hops under 2 km
docs: update installation instructions
refactor: share the trip sequence between crimes
```

## Versioning

This project uses [Commitizen](https://commitizen-tools.github.io/commitizen/) (`cz`) for versioning and changelog generation.

### Creating Releases

When you're ready to release, run on `main`:

```bash
cz bump
```

This will:
- Bump the version in `pyproject.toml` and `package.json` based on commit history
- Update `CHANGELOG.md`
- Create a git tag

Then push the commit and the tag:

```bash
git push --follow-tags origin main
```

Pushing a version tag triggers `.github/workflows/build.yml`, which builds both images, pushes them to `ghcr.io/gtfs-zone/gtfs-zone-crimes` (the Dagster code location) and `ghcr.io/gtfs-zone/gtfs-zone-crimes-web` (the site), and records their digests in [gtfs-zone-infra](https://github.com/gtfs-zone/gtfs-zone-infra). ArgoCD then rolls them out to <https://crimes.gtfs.zone>.

## Development Workflow

1. Create a feature branch from `main`
2. Make your changes
3. Commit using `pnpm commit` (this ensures proper commit format)
4. Push your branch and create a pull request
5. After merge to `main`, run `cz bump` for releases when ready

## Adding a crime

1. A module in `src/gtfs_zone_crimes/crimes/` with a `CRIME = Crime(...)`: a slug, a scope (what it is judged on) and a judge returning a `Verdict`, or `None` when the feed cannot be judged.
2. Its entry in `CRIMES` in `src/gtfs_zone_crimes/registry.py`; the site lists crimes in this order, most notable first, so place it by notability.
3. Its write-up in `content/crimes/<slug>.md`: frontmatter `title` and `tagline` (and optionally `featured`, a feed id shown as Exhibit A), then the case against it, the law, and how to get pardoned.
4. Tests in `tests/` that convict and acquit it, starting from the clean fixture.

A new release judges every zip again, so a changed rule takes effect on the next run after the release. When a change could acquit feeds that did not change, bump the crime's `revision`: acquittals across a revision are dropped instead of pardoned, and the old revision's pardons are cleared.

## Git Hooks

Hooks are defined in `.pre-commit-config.yaml` and run by [prek](https://github.com/j178/prek). Install them once per clone:

```bash
uv tool install prek
prek install
```

- **pre-commit**: Runs the repo's checks
- **commit-msg**: Validates commit message format using commitizen

If your commit message doesn't follow the conventional format, the commit will be rejected with a helpful error message.
