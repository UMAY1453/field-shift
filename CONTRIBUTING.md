# Contributing to Field Shift

Thank you for helping improve Field Shift. Contributions are welcome when they preserve the project's goals: transparent climate evidence, explainable agricultural decision support, reproducible data handling, and a reliable public demo.

Please read this guide and [CONTRACTS.md](CONTRACTS.md) before changing shared API fields or data structures.

## 1. Project Principles

Contributions should:

- keep the public workflow understandable for farmers and decision-makers;
- distinguish historical evidence from weather forecasts;
- preserve source attribution and visible limitations;
- avoid presenting prototype scores as guaranteed agronomic advice;
- keep valid zero values distinct from missing values;
- fail explicitly instead of fabricating climate or recommendation results;
- include tests proportional to the behavior changed;
- avoid secrets, credentials, personal data, and proprietary datasets.

## 2. Ways to Contribute

Useful contributions include:

- bug fixes;
- tests and edge-case coverage;
- accessibility and responsive-interface improvements;
- clearer English or Turkish localization;
- documentation corrections;
- verified crop-source improvements;
- data-quality and NASA POWER resilience improvements;
- performance improvements that preserve deterministic behavior;
- proposals for new regions backed by validation evidence.

For substantial API, scoring, data-source, or architecture changes, open an issue or discuss the proposal with the maintainers before implementation.

## 3. Development Setup

### Clone the repository

```bash
git clone https://github.com/UMAY1453/field-shift.git
cd field-shift
```

### Create a virtual environment

Windows PowerShell:

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Run the application

```bash
python -m uvicorn backend.main:app --reload
```

Open:

- application: <http://127.0.0.1:8000>
- API documentation: <http://127.0.0.1:8000/docs>
- health endpoint: <http://127.0.0.1:8000/api/health>

FastAPI serves both the frontend and API. A second frontend server is not required.

## 4. Branch and Pull-Request Workflow

Do not develop directly on `main`.

1. Synchronize your local `main`:

   ```bash
   git switch main
   git pull origin main
   ```

2. Create a focused branch:

   ```bash
   git switch -c feature/short-description
   ```

   Recommended prefixes include `feature/`, `fix/`, `docs/`, `test/`, and `refactor/`.

3. Make one focused change at a time.
4. Run the relevant tests and inspect the final diff.
5. Push the branch and open a pull request against `main`.

If you do not have write access, fork the repository, push your branch to the fork, and open a pull request from that branch.

Avoid force-pushing a branch after review has started unless reviewers agree.

## 5. Commit Messages

Use short, descriptive commit messages. Conventional prefixes are encouraged:

| Prefix | Use |
|---|---|
| `feat` | New user-visible behavior |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Test addition or correction |
| `refactor` | Internal change without intended behavior change |
| `chore` | Tooling, dependency, or repository maintenance |
| `style` | Visual or formatting change |

Examples:

```text
feat: add historical harvest-window summary
fix: preserve zero precipitation values
test: cover NASA rate-limit retry behavior
docs: clarify rolling reference period
```

Avoid vague messages such as `update`, `changes`, or `final`.

## 6. Testing

Run the full suite before requesting review:

```bash
python -m pytest -q
```

For detailed output:

```bash
python -m pytest -v
```

Run an individual module when iterating:

```bash
python -m pytest tests/test_nasa_service.py -q
```

The current final suite contains 179 tests. A contribution may change that number; the requirement is that all applicable tests pass.

New or changed behavior should cover, where relevant:

- successful behavior;
- missing and `null` values;
- valid zero values;
- invalid types and ranges;
- duplicate and missing dates;
- NASA fill values such as `-999`;
- timeout, connection, rate-limit, and unavailable-service behavior;
- cache and fallback behavior;
- deterministic recommendation ordering;
- public request and response validation.

Manual browser checks are useful but do not replace automated tests.

## 7. API and Contract Changes

Public requests and responses are defined in [CONTRACTS.md](CONTRACTS.md) and enforced by Pydantic models.

Before changing a shared field:

1. explain why the change is required;
2. identify frontend, backend, data, and test impact;
3. update `CONTRACTS.md`;
4. update the Pydantic request/response models;
5. update all producers and consumers;
6. add or update automated tests;
7. describe migration or compatibility impact in the pull request.

Do not silently rename fields or change units.

Stable conventions include:

- `snake_case` JSON fields;
- ISO `YYYY-MM-DD` dates;
- Celsius temperatures;
- millimetres of precipitation;
- `0-100` scores;
- `null` for missing numeric measurements;
- real zero values preserved as observations.

## 8. Climate Data Contributions

The primary climate source is the NASA POWER Daily API.

Climate changes must preserve:

- backend-only NASA requests;
- `community=AG`;
- `format=JSON`;
- `time-standard=LST`;
- the six contracted parameters;
- safe conversion of NASA fill values;
- bounded retry and concurrency behavior;
- transparent `live`, `cache`, and `demo` source reporting;
- source warnings and fallback disclosure.

Do not commit generated cache files. The verified Bursa snapshot is a reviewed project dataset and must not be replaced without documenting its source, coordinate, date range, record count, validation process, and impact on tests.

## 9. Crop Data and Sources

Changes to `backend/data/crops.json` require particular care.

Every crop entry must satisfy the Pydantic schema and include source objects with:

- a human-readable title;
- a usable URL;
- a non-empty list of fields supported by that source.

Do not invent unsupported numeric thresholds. If a value cannot be verified, prefer an allowed `null` value and disclose the limitation.

When translating a source statement into a normalized field:

- preserve the source's scope and conditions;
- avoid converting a qualitative statement into unsupported precision;
- distinguish optimum ranges from absolute tolerance limits;
- keep crop identifiers stable;
- add or update crop-data and recommendation tests.

`fallow` remains a special previous-field state and must not be added as a crop.

## 10. Frontend Contributions

Frontend changes should:

- remain responsive on desktop and mobile screens;
- preserve keyboard and readable-label accessibility;
- use the backend API rather than calling NASA POWER;
- display source mode, warnings, data completeness, and limitations honestly;
- avoid describing historical harvest evidence as a forecast;
- keep user-facing errors concise and non-technical;
- preserve same-origin production behavior;
- continue supporting optional port-`5500` local frontend development where practical.

When changing chart or card behavior, test realistic, missing, zero, and empty-result states.

## 11. Documentation Contributions

The repository's primary global documentation is English. User-facing application text may remain localized for the Bursa pilot.

Documentation must:

- match the current implementation;
- distinguish examples from permanently fixed behavior;
- use the stable production URL where needed;
- keep NASA POWER and agronomic-source attribution visible;
- state the Bursa pilot scope and limitations;
- avoid claiming a weather forecast, yield guarantee, or universal agronomic validity.

Documentation-only changes do not require a Vercel deployment.

## 12. Dependencies and Configuration

Do not add a runtime dependency unless the standard library or an existing dependency cannot reasonably solve the problem.

For every proposed dependency:

- explain its purpose;
- verify its license is compatible with Apache License 2.0;
- pin or constrain it consistently;
- update both local and deployment dependency definitions when applicable;
- add tests for the behavior it enables.

Do not commit:

- `.venv/`;
- `.vercel/`;
- cache files;
- editor-specific state;
- credentials, tokens, or `.env` files;
- generated temporary data.

Never edit `.git/` or virtual-environment files manually.

## 13. Pull-Request Checklist

Before opening a pull request, confirm:

- [ ] The branch contains one focused change.
- [ ] The working tree contains no accidental generated files.
- [ ] The implementation matches `CONTRACTS.md`.
- [ ] Relevant tests were added or updated.
- [ ] The full applicable test suite passes.
- [ ] JSON data files parse successfully.
- [ ] No secret, token, credential, or personal data is included.
- [ ] Source attribution is preserved.
- [ ] User-visible limitations remain clear.
- [ ] Documentation is updated when behavior changes.
- [ ] The public demo was checked when deployment behavior changes.

A pull-request description should include:

- the problem being solved;
- the chosen approach;
- the primary files changed;
- tests performed and results;
- screenshots for visible changes;
- known limitations or follow-up work;
- contract and deployment impact.

## 14. JSON Validation

PowerShell examples:

```powershell
Get-Content "backend\data\crops.json" -Raw | ConvertFrom-Json | Out-Null
Get-Content "backend\data\demo_climate.json" -Raw | ConvertFrom-Json | Out-Null
```

Python can also be used:

```bash
python -m json.tool backend/data/crops.json > /dev/null
python -m json.tool backend/data/demo_climate.json > /dev/null
```

## 15. Security and Responsible Reporting

Do not open a public issue containing a secret, credential, personal location history, or exploitable deployment detail.

The NASA POWER endpoint used by this project does not require an API key. Never add unrelated service credentials to the repository.

For a suspected vulnerability, contact a repository maintainer privately when possible and provide:

- the affected component;
- reproduction steps;
- expected impact;
- a proposed mitigation, if known.

## 16. Deployment Notes

The public Vercel deployment is maintained by the project team. External contributors are not expected to deploy production.

Maintainers must deploy application-code changes to the existing Vercel project and preserve the stable alias encoded by the presentation QR code:

```text
https://field-shift-mocha-sigma.vercel.app
```

Creating a new Vercel project is not a replacement for updating the existing production deployment. Documentation-only changes require only a repository commit and do not require redeployment.

## 17. License

By contributing, you agree that your contribution may be distributed under the repository's [Apache License 2.0](LICENSE).
