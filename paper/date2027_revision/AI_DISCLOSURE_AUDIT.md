# Generative-AI disclosure audit

Audit date: 2026-09-10

## Applicable rules

- DATE 2027 states that submissions follow the IEEE policy on AI-generated
  content and that review is double blind:
  <https://www.date-conference.com/call-for-papers>
- IEEE's conference submission policy states that AI-generated content must be
  disclosed in the acknowledgments, naming the system and identifying the
  sections and extent of use. Editing and grammar assistance alone does not
  require disclosure, although disclosure is recommended:
  <https://conferences.ieeeauthorcenter.ieee.org/author-ethics/guidelines-and-policies/submission-policies/>

## Use classification

The assistance here was substantive rather than grammar-only: OpenAI Codex
helped restructure and draft manuscript language and helped produce plotting
and validation scripts. Disclosure is therefore required under the cited IEEE
policy.

## Implemented disclosure

`main.tex` contains this anonymous, non-project-specific statement in an
unnumbered acknowledgment on technical page 6:

> Generative-AI disclosure: The authors used OpenAI Codex to assist with
> manuscript restructuring and language drafting in the Abstract,
> Introduction, Related Work, Discussion, and Conclusion, and with plotting
> and validation scripts. The authors checked all technical claims,
> calculations, citations, and final text against the cited literature and
> frozen repository evidence; the system was not used as an author or evidence
> source.

## Blind-review check

- The disclosure names the system and extent of use but contains no author,
  institution, grant, repository owner, or project identifier.
- The author block reads `Anonymous submission`.
- No ordinary project acknowledgment is present.
- The disclosure is on a technical page; the seventh page remains
  references-only.

Result: **PASS**, subject to rechecking the live DATE submission portal if its
2027 author instructions change before upload.
