# GREEN Matrix 3.1 evidence-kind extension

Evidence tier and evidence kind are independent.  This campaign uses the
frozen E0-E7 tier meanings and explicitly distinguishes these kinds:

| Kind | Meaning |
|---|---|
| `MEASURED` | Direct observation inside the declared measurement boundary. |
| `DERIVED_FROM_MATCHED_MEASUREMENT` | Unit-safe derivation from matched measured inputs. |
| `ANALYTICAL` | Equation, RTL contract, or exact logical result. |
| `POST_ROUTE_ESTIMATE` | Tool result or derivation from a post-route estimate. |
| `LITERATURE_REFERENCE` | Published value retained in its native applicable boundary. |
| `PARAMETRIC` | Explicit user/research parameter, not a measurement. |
| `BOUND` | Defensible one- or two-sided bound. |
| `EXPLICIT_ZERO` | A physically or definitionally justified zero. |
| `EXCLUDED` | Outside the declared system boundary. |
| `UNAVAILABLE` | Required evidence does not exist in the campaign. |
| `TECHNOLOGY_MISMATCH` | Evidence exists but does not match target technology/process/geometry. |
| `BLOCKED` | A result cannot be evaluated because prerequisite evidence is absent or inapplicable. |

No kind is converted into another implicitly.  In particular, the seed-11
power integration remains `POST_ROUTE_ESTIMATE`; literature from a nominally
130-nm process remains `TECHNOLOGY_MISMATCH` for SKY130; and structural
missingness remains `UNAVAILABLE`, not a numerical uncertainty interval.
