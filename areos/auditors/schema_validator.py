# areos/auditors/schema_validator.py
#
# Task 3b: Schema.org / JSON-LD Validator
#
# CONTRACT:
#   - Receives a list of JSON-LD objects (from the crawler's extraction layer).
#   - Validates each against known schema.org type rules.
#   - Returns a list of ValidationResult objects — deterministic, no LLM involved.
#
# SUPPORTED TYPES (initial set — most common in AEO/GEO audits):
#   - Organization, LocalBusiness, WebPage, Article, FAQPage, HowTo, Product, BreadcrumbList
#
# VALIDATION RULES:
#   - required_fields: MUST be present and non-empty.
#   - recommended_fields: SHOULD be present; absence is a warning.
#   - known_fields: full list of recognized fields for this type (unknown keys flagged).

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# ── Schema rule definitions ──────────────────────────────────────────────────

SCHEMA_RULES: dict[str, dict] = {
    "Organization": {
        "required": ["@type", "name"],
        "recommended": ["url", "logo", "sameAs", "contactPoint", "description"],
        "known": ["@context", "@type", "@id", "name", "url", "logo", "sameAs",
                  "description", "address", "contactPoint", "founder", "foundingDate",
                  "email", "telephone", "legalName", "alternateName", "numberOfEmployees",
                  "parentOrganization", "subOrganization", "areaServed", "award",
                  "knowsAbout", "memberOf", "owns", "sponsor", "hasOfferCatalog",
                  "image", "potentialAction"],
    },
    "LocalBusiness": {
        "required": ["@type", "name", "address"],
        "recommended": ["telephone", "openingHours", "geo", "url", "priceRange", "image"],
        "known": ["@context", "@type", "@id", "name", "url", "address", "telephone",
                  "openingHours", "openingHoursSpecification", "geo", "image", "logo",
                  "priceRange", "currenciesAccepted", "paymentAccepted", "menu",
                  "servesCuisine", "starRating", "aggregateRating", "review",
                  "hasMap", "sameAs", "description", "email", "faxNumber",
                  "branchCode", "department"],
    },
    "WebPage": {
        "required": ["@type", "name"],
        "recommended": ["url", "description", "author", "datePublished", "dateModified"],
        "known": ["@context", "@type", "@id", "name", "url", "description", "author",
                  "datePublished", "dateModified", "publisher", "inLanguage",
                  "breadcrumb", "image", "primaryImageOfPage", "significantLink",
                  "speakable", "specialty", "relatedLink", "about", "mentions",
                  "keywords", "mainEntity", "mainContentOfPage"],
    },
    "Article": {
        "required": ["@type", "headline", "author", "datePublished"],
        "recommended": ["dateModified", "description", "image", "publisher",
                        "mainEntityOfPage", "keywords"],
        "known": ["@context", "@type", "@id", "headline", "name", "url", "description",
                  "author", "datePublished", "dateModified", "image", "publisher",
                  "mainEntityOfPage", "keywords", "articleSection", "wordCount",
                  "inLanguage", "about", "mentions", "citation", "isPartOf",
                  "thumbnailUrl", "articleBody"],
    },
    "FAQPage": {
        "required": ["@type", "mainEntity"],
        "recommended": ["name", "url"],
        "known": ["@context", "@type", "@id", "name", "url", "description",
                  "mainEntity", "about", "inLanguage"],
    },
    "Question": {
        "required": ["@type", "name", "acceptedAnswer"],
        "recommended": [],
        "known": ["@context", "@type", "@id", "name", "text", "acceptedAnswer",
                  "suggestedAnswer", "upvoteCount", "answerCount", "dateCreated",
                  "author", "comment"],
    },
    "Answer": {
        "required": ["@type", "text"],
        "recommended": ["url"],
        "known": ["@context", "@type", "@id", "text", "url", "upvoteCount",
                  "dateCreated", "author", "comment"],
    },
    "HowTo": {
        "required": ["@type", "name", "step"],
        "recommended": ["description", "image", "totalTime", "supply", "tool"],
        "known": ["@context", "@type", "@id", "name", "url", "description", "image",
                  "estimatedCost", "supply", "tool", "totalTime", "step",
                  "prepTime", "performTime", "yield"],
    },
    "Product": {
        "required": ["@type", "name"],
        "recommended": ["description", "image", "offers", "brand", "sku", "gtin",
                        "aggregateRating", "review"],
        "known": ["@context", "@type", "@id", "name", "url", "description", "image",
                  "offers", "brand", "sku", "gtin", "gtin8", "gtin12", "gtin13",
                  "gtin14", "mpn", "color", "material", "aggregateRating", "review",
                  "additionalProperty", "category", "logo", "manufacturer",
                  "productID", "releaseDate", "weight", "width", "height", "depth",
                  "isSimilarTo", "isRelatedTo", "isVariantOf"],
    },
    "BreadcrumbList": {
        "required": ["@type", "itemListElement"],
        "recommended": [],
        "known": ["@context", "@type", "@id", "itemListElement", "name", "url",
                  "numberOfItems", "itemListOrder"],
    },
    "ListItem": {
        "required": ["@type", "position"],
        "recommended": ["item", "name", "url"],
        "known": ["@context", "@type", "@id", "position", "item", "name", "url",
                  "nextItem", "previousItem"],
    },
}

# ── Result data structure ─────────────────────────────────────────────────────

@dataclass
class SchemaIssue:
    severity: str        # "error" | "warning" | "info"
    code: str            # machine-readable short code
    message: str

@dataclass
class ValidationResult:
    schema_type: str
    index: int           # which JSON-LD block on the page (0-indexed)
    passed: bool
    issues: list[SchemaIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


# ── Core validation logic ─────────────────────────────────────────────────────

def _is_empty(value: Any) -> bool:
    """Return True if the value is None, empty string, or empty collection."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def validate_single(block: dict, index: int = 0) -> ValidationResult:
    """
    Validate one JSON-LD block against schema.org rules.
    Returns a ValidationResult with granular issues.
    """
    # Resolve @type — may be a list or string
    raw_type = block.get("@type", "")
    if isinstance(raw_type, list):
        raw_type = raw_type[0] if raw_type else ""
    schema_type = raw_type.strip()

    if not schema_type:
        return ValidationResult(
            schema_type="Unknown",
            index=index,
            passed=False,
            issues=[SchemaIssue("error", "MISSING_TYPE", "@type field is missing or empty")]
        )

    rules = SCHEMA_RULES.get(schema_type)
    if rules is None:
        return ValidationResult(
            schema_type=schema_type,
            index=index,
            passed=True,
            issues=[SchemaIssue(
                "info", "UNKNOWN_SCHEMA_TYPE",
                f"Schema type '{schema_type}' has no validation rules defined — manual review recommended"
            )]
        )

    issues: list[SchemaIssue] = []

    # 1. Required field checks
    for req in rules["required"]:
        if req not in block or _is_empty(block.get(req)):
            issues.append(SchemaIssue(
                "error", "MISSING_REQUIRED_FIELD",
                f"Required field '{req}' is missing or empty"
            ))

    # 2. Recommended field checks
    for rec in rules["recommended"]:
        if rec not in block or _is_empty(block.get(rec)):
            issues.append(SchemaIssue(
                "warning", "MISSING_RECOMMENDED_FIELD",
                f"Recommended field '{rec}' is absent — may reduce AI retrieval quality"
            ))

    # 3. Unknown field check
    known = set(rules["known"])
    for key in block:
        if key not in known:
            issues.append(SchemaIssue(
                "warning", "UNKNOWN_FIELD",
                f"Field '{key}' is not a recognized property of {schema_type}"
            ))

    # 4. FAQPage-specific: validate nested Question items
    if schema_type == "FAQPage":
        main_entity = block.get("mainEntity", [])
        if isinstance(main_entity, dict):
            main_entity = [main_entity]
        for qi, question in enumerate(main_entity):
            q_result = validate_single(question, index=qi)
            for issue in q_result.issues:
                issues.append(SchemaIssue(
                    issue.severity, issue.code,
                    f"mainEntity[{qi}]: {issue.message}"
                ))

    passed = not any(i.severity == "error" for i in issues)
    return ValidationResult(schema_type=schema_type, index=index, passed=passed, issues=issues)


def validate_page_schemas(json_ld_blocks: list) -> list[ValidationResult]:
    """
    Validate all JSON-LD blocks extracted from a page.
    Accepts the raw output of the existing crawler's json_lds list.
    """
    results = []
    for idx, block in enumerate(json_ld_blocks):
        if isinstance(block, str):
            # Block was unparseable (flagged by the existing crawler already)
            results.append(ValidationResult(
                schema_type="Unparseable",
                index=idx,
                passed=False,
                issues=[SchemaIssue(
                    "error", "JSON_PARSE_FAILURE",
                    f"JSON-LD block at index {idx} could not be parsed as valid JSON"
                )]
            ))
            continue

        if not isinstance(block, (dict, list)):
            results.append(ValidationResult(
                schema_type="Invalid",
                index=idx,
                passed=False,
                issues=[SchemaIssue("error", "INVALID_STRUCTURE",
                                    "JSON-LD block is not an object or array")]
            ))
            continue

        # Handle @graph wrapper
        if isinstance(block, list):
            for sub_idx, sub_block in enumerate(block):
                results.append(validate_single(sub_block, index=idx * 1000 + sub_idx))
            continue

        if "@graph" in block:
            for sub_idx, sub_block in enumerate(block["@graph"]):
                results.append(validate_single(sub_block, index=idx * 1000 + sub_idx))
            continue

        results.append(validate_single(block, index=idx))

    return results


def format_report(url: str, results: list[ValidationResult]) -> str:
    """
    Format the validation results as a human-readable string for CLI output
    or embedding in reports.
    """
    lines = [f"Schema Validation Report for: {url}", "=" * 60]
    if not results:
        lines.append("No JSON-LD blocks found on this page.")
        return "\n".join(lines)

    total_errors = sum(r.error_count for r in results)
    total_warnings = sum(r.warning_count for r in results)
    passed = sum(1 for r in results if r.passed)

    lines.append(
        f"Summary: {len(results)} block(s) | {passed} passed | "
        f"{total_errors} error(s) | {total_warnings} warning(s)\n"
    )

    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        lines.append(f"[Block {result.index}] {result.schema_type} — {status}")
        for issue in result.issues:
            icon = {"error": "  ✗", "warning": "  ⚠", "info": "  ℹ"}.get(issue.severity, "  ?")
            lines.append(f"{icon} [{issue.code}] {issue.message}")
        lines.append("")

    return "\n".join(lines)
