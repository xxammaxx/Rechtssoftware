# Research — M6-B Calendar Context and Versioned Legal Rule Profiles

**Status:** `RESEARCH_PASS_WITH_HUMAN_LEGAL_REVIEW_REQUIRED`
**Accessed:** 2026-07-26
**Source policy:** the normative matrix below uses only official federal or state publication/legislation portals. It is a research and provenance design, not a statement that any rule applies to a user’s facts.

## Findings that constrain the design

1. § 193 BGB describes a consequence for a specified day or last day of a period when a Sunday, recognised general holiday at the declaration/performance place, or Saturday is involved. It therefore requires factual and territorial predicates; a displayed weekend is not enough to apply it.
2. § 222 ZPO expressly links procedural time calculation to the BGB and separately describes end-of-period and hour-period handling. It is process-specific and cannot be selected for a non-procedural case by software.
3. § 41 VwVfG and § 4 VwZG contain delivery/announcement constructs with conditions and rebuttal/proof consequences. They are deliberately deferred to M6-B.4.
4. Holiday laws are state-specific and can include temporal, territorial or exceptional qualifications. A calendar library or an unversioned “German holidays” list is insufficient as a legal source.

## Rule research matrix

| Norm | Absatz/Satz | Jurisdiction | Valid from / to | Trigger | Preconditions / exceptions | Candidate outcome | Uncertainty | Human review |
|---|---|---|---|---|---|---|---|---|
| [§ 193 BGB](https://www.gesetze-im-internet.de/bgb/__193.html) | whole provision | Federal civil law; factual declaration/performance place matters | current text must be captured by profile version; no perpetual assumption | specified day or final day of a period falls on Sunday, recognised general holiday or Saturday | scope and place must be established; product must not infer them | potential next working day rule | applicability and holiday recognition are factual/legal questions | mandatory; profile selection plus source/date/place confirmation |
| [§ 222 ZPO](https://www.gesetze-im-internet.de/zpo/__222.html) | (1)–(3) | Civil procedure | profile must state source version/date | procedural period | procedural context, period type and any special rule must be established | potential procedural calculation rule | whether ZPO governs is not inferable | mandatory; unsupported unless an explicitly approved profile covers it |
| [§ 41 VwVfG](https://www.gesetze-im-internet.de/vwvfg/__41.html) | (1), (2), (2a), (4), (5) | Federal administrative procedure subject to scope | profile must capture temporal text version | notice/announcement of administrative act | channel, dispatch, access, exceptions and proof must be established | no first-build outcome | factual delivery and statutory scope are high-risk | M6-B.4 only; separate norm/application review |
| [§ 4 VwZG](https://www.gesetze-im-internet.de/vwzg_2005/__4.html) | (1)–(2) | Federal administrative service | profile must capture temporal text version | postal registered delivery | delivery method, posting date, receipt/late receipt and evidence must be established | no first-build outcome | conditions and rebuttal cannot be guessed | M6-B.4 only; separate norm/application review |

## Holiday-source foundation

The first build does **not** ship a holiday file. Its acceptance condition is a repository format that can later record a reviewed source per record. The source registry must use the official portal or official publication for each state and preserve the source text version/date in the dataset provenance. Representative official primary sources checked during this specification are listed below; the full dataset-ingestion review must verify every individual record, including municipal/regional exceptions, before any record is released.

| Jurisdiction | Official primary source / portal | Dataset implication |
|---|---|---|
| Baden-Württemberg | [Landesrecht BW — Feiertagsgesetz](https://www.landesrecht-bw.de/bsbw/?query=DOKNR%3Ajlr-FeiertGBWV2P10&source=PermaLink) | Source version and locality exceptions must be represented. |
| Bayern | [Bayern.Recht — Feiertagsgesetz](https://www.gesetze-bayern.de/Content/Document/BayFTG) | State and municipality-scoped records must be distinguishable. |
| Berlin | [Gesetze Berlin — FeiertG BE](https://gesetze.berlin.de/bsbe/document/jlr-FeiertGBErahmen) | Validity interval is source data, not an application assumption. |
| Brandenburg | [BRAVORS — Feiertagsgesetz](https://bravors.brandenburg.de/gesetze/ftg_2015) | State legislation and any one-off ordinance need separate provenance. |
| Bremen | [Transparenzportal Bremen — Sonn-, Gedenk- und Feiertage](https://www.transparenz.bremen.de/metainformationen/gesetz-ueber-die-sonn-gedenk-und-feiertage-vom-12-november-1954-145882) | Official publication references remain record-level evidence. |
| Hamburg | [Hamburg Landesrecht portal](https://www.hamburg.de/politik-und-verwaltung/service/landesrecht) | Exact source/version must be captured before a record ships. |
| Hessen | [Hessenrecht — HFeiertagsG](https://www.rv.hessenrecht.hessen.de/bshe/?query=DOKNR%3Ajlr-FeiertGHE1952rahmen) | Effective-date/version field is mandatory. |
| Mecklenburg-Vorpommern | [Landesrecht M-V portal](https://www.landesrecht-mv.de/) | Exact official record and effective period must be reviewed before inclusion. |
| Niedersachsen | [NI-VORIS — NFeiertagsG](https://voris.wolterskluwer-online.de/browse/document/b724111b-6c20-3862-b111-589842acacba) | Historical version selection is required. |
| Nordrhein-Westfalen | [RECHT.NRW — Landesrecht/GVBl](https://recht.nrw.de/) | Official statute version must be pinned in provenance. |
| Rheinland-Pfalz | [RLP Interior — Sonn- und Feiertagsrecht](https://mdi.rlp.de/themen/buerger-und-staat/verfassung-und-verwaltung/sonn-und-feiertagsrecht) | Source record must link statutory text, not a calendar summary. |
| Saarland | [Saarland Landesrecht](https://www.saarland.de/arbg/DE/landesrecht) | Exact official statute/version must be reviewed before inclusion. |
| Sachsen | [REVOSax — SächsSFG](https://www.revosax.sachsen.de/vorschrift/3997.2) | Regional exceptions must not be flattened to state-wide flags. |
| Sachsen-Anhalt | [Landesrecht Sachsen-Anhalt](https://mj.sachsen-anhalt.de/service/recht-und-gesetz/landesrecht/) | Each effective date must be explicit. |
| Schleswig-Holstein | [Landesrecht Schleswig-Holstein](https://www.schleswig-holstein.de/DE/landesportal/service/Landesrecht/landesrecht_online) | Verify statutory source and temporal scope before shipping. |
| Thüringen | [Thüringen Landesrecht](https://landesrecht.thueringen.de/) | Exact official record and effective period must be reviewed before inclusion. |

The registry list is not a production holiday dataset and conveys no holiday date. Its purpose is to prevent later use of a third-party calendar feed or a source-less table.

## Source version and temporal-validity policy

- Each profile and holiday record is associated with `valid_from`, optional `valid_to`, `source_url`, `source_published_at` when known, `reviewed_at`, and a source-content SHA-256.
- A date outside `valid_from..valid_to`, an absent source hash, or an unreviewed source blocks a rule result.
- “Current law” is never a substitute for a recorded source version. Historic facts must be evaluated with a source version covering the relevant date.
- A source update creates a new immutable dataset/profile version; it never silently mutates an old calculation trace.

## Delivery and announcement fictions: explicit deferral

The official texts above establish that these areas depend on legally and factually significant conditions (type of act/document, channel, dispatch, receipt and proof). Consequently, M6-B.4 has its own future specification, source review, red tests and owner approval. The first M6-B implementation must report `DELIVERY_FICTION_OUT_OF_SCOPE` rather than calculate a fictional date.

## Technical basis

ISO-8601 calendar dates and the Python standard-library date model are suitable for deterministic weekday arithmetic. They do not encode German legal applicability. The data and profile layer, not the date library, provides source/version provenance.
