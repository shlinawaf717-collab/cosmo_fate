# Preregistration provenance audit

Audit date: 2026-07-21; extended 2026-07-22 (Asia/Shanghai)

## Scope of the claim

The protocol was written and frozen in local version control before the first
target fate calculation, according to the preserved Git history. Because the
repository was made public only afterwards, the original freeze lacks an
independently verifiable timestamp. We therefore describe the study as locally
preregistered, not as a registry-verified preregistration.

The present public repository preserves the preregistration and its full
descendant history. The limitation concerns external verification of the
original freeze time; it is not a claim that the plan was written
retrospectively.

The precise scope is a **secondary-data preregistration of the fate-translation
audit**. The datasets and validation strategy were already known; the claim is
that the core classifier, audit axes, gates, and reportable outcome forms were
frozen before the first target fate calculation. It is not a claim that the
plan preceded data access.

## Frozen plan

- Commit: `98abc2017421f6825e8a2aa36f7cb76b5661db76`
- Historical tag: `prereg-v1` (lightweight tag resolving to the commit above)
- Commit subject: `preregister analysis plan v1`
- Author and commit time: `2026-07-03T10:26:34+08:00`
- Tree: `c7208da5cae9c5916f1a6c9e61afa8a4cb926d0c`
- Frozen file: `plan/ANALYSIS_PLAN.md`
- SHA-256 of that file as stored at `prereg-v1`:
  `f9c25bb5f2210d93ba5874103a3f7a1b074afaab82e9d9be4541990bb8af98fc`

The commit contains the analysis plan, initial amendment log, data manifest,
and workspace README. The plan declares the model family, priors, dataset
combinations, fate classifier, fragility metrics, gates, and two outcome forms.

## First target result

- Commit: `76ed25db138a42976548739fa09fcf52cc618751`
- Commit subject: `Phase 2 first result: D0+CPL+P1 fate probabilities (DECAY
  99.8%, RIP 0.18%±0.06% pre-verification)`
- Author and commit time: `2026-07-03T11:29:03+08:00`
- Tree: `c5f3338750a48a2f33ab5eb65d0b36165d0a9347`
- First result artifact: `runs/phase2/fate/d0_cpl_p1.json`

The recorded interval between the plan freeze and the first target result is
1 hour, 2 minutes, and 29 seconds.

Git confirms that `prereg-v1` is an ancestor of the first-result commit. The
ancestry path is:

1. `982fb00771fee54f945cdc7273d490d223db58cf` — Phase-1 pipeline and A-001
2. `51d073f5483d897b7e01dd29337dc8c654eed4e3` — Gate-1 validation
3. `435f7fbaacead23a2cece0e3164218859704176e` — fate classifier and A-001 sign-off
4. `76ed25db138a42976548739fa09fcf52cc618751` — first target fate result

## Grammar-specific P1 implementation trace

The frozen P1 table states the early-matter-domination intent and gives its CPL
form, `w0+wa<0`; it does not enumerate the corresponding condition for every
registered grammar. The archived implementations use:

- CPL: `w0+wa<0`, because `w(z->infinity)->w0+wa`;
- JBP and BA: `w0<0`, because `w(z->infinity)->w0`;
- BIN4: `w4<0`, where `w4` is the highest-redshift bin;
- GP: the conditional-mean construction reverts to `w=-1`, but the fitted GP
  failed Gate 3 and is excluded from quantitative fit comparisons.

The model-specific conditions, `runs/phase3/fparam/PRIOR_NOTE.md`, and the first
F-parametrization outputs were first archived together in commit
`777816f57a854cd4d1ec81fb35d7d916b36cad8c` at
`2026-07-06T13:17:09+08:00`. The present history therefore establishes the
implementation used by those runs but does not independently establish the
within-commit order of the translation choice and the run outputs. A-007 records
this limitation without retroactively treating the model-specific formulas as
explicitly preregistered text. A-006 later strengthened the BIN4 condition with
`rho_DE/rho_m(z=1059)<0.01`; the archived posterior passes that gate with zero
weighted violating mass.

## Public-repository timing and limitation

The GitHub repository API reports `created_at = 2026-07-07T02:43:17Z`
(`2026-07-07 10:43:17+08:00`), after the initial analysis. Consequently:

- the present Git history documents a coherent pre-result plan-to-result order;
- commit hashes make the now-public archived objects content-addressable;
- the GitHub creation record does **not** independently prove that the local
  commit already existed at its recorded 2026-07-03 time;
- the project must not describe this as an OSF-style or independently
  timestamped public preregistration.

The [Center for Open Science registry guidance](https://help.osf.io/article/330-welcome-to-registrations)
defines preregistration in its registry workflow as a time-stamped, read-only
plan posted before analysis. This project followed the advance-plan and
frozen-record components locally, but not the third-party registry component at
freeze time. Future studies should deposit the frozen plan in OSF, Zenodo, or
another immutable timestamp service before any target analysis.

## Reproduction commands

```bash
git rev-parse 'prereg-v1^{commit}'
git cat-file -t prereg-v1
git show -s --format=fuller prereg-v1
git show prereg-v1:plan/ANALYSIS_PLAN.md | shasum -a 256
git merge-base --is-ancestor prereg-v1 76ed25db138a42976548739fa09fcf52cc618751
git rev-list --ancestry-path --reverse prereg-v1..76ed25db138a42976548739fa09fcf52cc618751
gh api repos/shlinawaf717-collab/cosmo_fate --jq '{created_at,html_url}'
```
