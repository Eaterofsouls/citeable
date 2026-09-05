# areos/auditors/entity_verifier.py
#
# Task T-204: Entity Verifier
#
# CONTRACT:
#   - Audits JSON-LD blocks for entity verification (Organization, LocalBusiness, Person).
#   - Validates entity naming, sameAs linkage completeness, and Wikidata/Wikipedia authority links.
#   - Emits structured finding objects with deterministic check codes.
#   - Boundary: Entity links only — no network requests, no URL validation.
#
# CHECK CODES:
#   - SAMEAS_MISSING (warning): Organization/LocalBusiness schema has no sameAs
#   - SAMEAS_INCOMPLETE (info): sameAs has fewer than 3 entries
#   - WIKIDATA_MISSING (warning): No Wikidata/Wikipedia link in sameAs
#   - ENTITY_NAME_MISSING (error): Organization/entity has no name field
#   - ENTITY_OK (info): Entity verification passed or no entity schema present

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ── Entity Type Definitions ──────────────────────────────────────────────────

ORGANIZATION_TYPES = {
    "Organization",
    "Corporation",
    "EducationalOrganization",
    "GovernmentOrganization",
    "NGO",
    "PerformingGroup",
    "Project",
    "SportsOrganization",
    "Airline",
    "Consortium",
    "FundingScheme",
    "LibrarySystem",
    "MedicalOrganization",
    "NewsMediaOrganization",
    "WorkersUnion",
    "ResearchOrganization",
}

LOCAL_BUSINESS_TYPES = {
    "LocalBusiness",
    "AnimalShelter",
    "ArchiveOrganization",
    "AutomotiveBusiness",
    "ChildCare",
    "Dentist",
    "DryCleaningOrLaundry",
    "EmergencyService",
    "EmploymentAgency",
    "EntertainmentBusiness",
    "FinancialService",
    "FoodEstablishment",
    "GovernmentOffice",
    "HealthAndBeautyBusiness",
    "HomeAndConstructionBusiness",
    "InternetCafe",
    "LegalService",
    "Library",
    "LodgingBusiness",
    "MedicalBusiness",
    "ProfessionalService",
    "RadioStation",
    "RealEstateAgent",
    "RecyclingCenter",
    "SelfStorage",
    "ShoppingCenter",
    "SportsActivityLocation",
    "Store",
    "TelevisionStation",
    "TouristInformationCenter",
    "TravelAgency",
    "Restaurant",
    "Bakery",
    "BarOrPub",
    "CafeOrCoffeeShop",
    "FastFoodRestaurant",
    "IceCreamShop",
    "Winery",
    "Brewery",
    "Hotel",
    "Motel",
    "Hostel",
    "BedAndBreakfast",
    "BankOrCreditUnion",
    "InsuranceAgency",
    "AccountingService",
    "Attorney",
    "Physician",
    "Hospital",
    "Pharmacy",
    "AutoRepair",
    "AutoDealer",
    "GasStation",
    "BeautySalon",
    "DaySpa",
    "HairSalon",
    "Electrician",
    "GeneralContractor",
    "HVACBusiness",
    "HousePainter",
    "Locksmith",
    "MovingCompany",
    "Plumber",
    "RoofingContractor",
}

PERSON_TYPES = {
    "Person",
    "Patient",
}


# ── Data Structures ──────────────────────────────────────────────────────────


@dataclass
class EntityIssue:
    severity: str  # "error" | "warning" | "info"
    code: str  # Check code in SCREAMING_SNAKE_CASE
    message: str


@dataclass
class EntityAuditResult:
    url: str
    passed: bool = True
    issues: list[EntityIssue] = field(default_factory=list)
    entities_found: list[dict] = field(default_factory=list)

    def __init__(
        self,
        url: str,
        passed: bool | list[EntityIssue] | None = None,
        issues: list[EntityIssue] | list[dict] | None = None,
        entities_found: list[dict] | None = None,
    ) -> None:
        self.url = url
        if isinstance(passed, list):
            # Positional call: EntityAuditResult(url, issues, entities_found)
            self.issues = passed
            self.entities_found = issues if isinstance(issues, list) else []
            self.passed = not any(getattr(i, "severity", "") == "error" for i in self.issues)
        else:
            self.passed = True if passed is None else bool(passed)
            self.issues = issues if isinstance(issues, list) else []
            self.entities_found = entities_found if isinstance(entities_found, list) else []

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "info")

    def as_finding_dicts(self, run_id: str = "LOCAL", site_id: str = "AUDIT") -> list[dict[str, Any]]:
        """Convert issues to finding dictionaries suitable for the synthesis engine."""
        return [
            {
                "code": issue.code,
                "check_code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
                "url": self.url,
                "check_type": "entity",
            }
            for issue in self.issues
        ]


# ── Internal Extraction Helpers ──────────────────────────────────────────────


def _extract_name(val: Any) -> str:
    """Extract a clean string representation of an entity name field."""
    def _sanitize(s: str) -> str:
        return s.strip()[:120]

    if isinstance(val, str):
        return _sanitize(val)
    if isinstance(val, dict):
        v = val.get("@value") or val.get("name") or ""
        if isinstance(v, str):
            return _sanitize(v)
    if isinstance(val, list) and val:
        first = val[0]
        if isinstance(first, str):
            return _sanitize(first)
        if isinstance(first, dict):
            v = first.get("@value") or first.get("name") or ""
            if isinstance(v, str):
                return _sanitize(v)
    return ""


def _extract_same_as(val: Any) -> list[str]:
    """Extract a list of sameAs URLs from string, list, or dict representations."""
    if isinstance(val, str):
        s = val.strip()
        return [s] if s else []
    if isinstance(val, list):
        urls: list[str] = []
        for item in val:
            if isinstance(item, str) and item.strip():
                urls.append(item.strip())
            elif isinstance(item, dict):
                url = item.get("@id") or item.get("url") or item.get("@value")
                if isinstance(url, str) and url.strip():
                    urls.append(url.strip())
        return urls
    return []


def _extract_types(block: dict) -> list[str]:
    """Extract normalized schema.org type names from a JSON-LD block."""
    raw = block.get("@type")
    if isinstance(raw, str):
        types = [raw]
    elif isinstance(raw, list):
        types = [t for t in raw if isinstance(t, str)]
    else:
        return []

    clean: list[str] = []
    for t in types:
        name = t.rsplit("/", 1)[-1].rsplit("#", 1)[-1].strip()
        if name.startswith("schema:"):
            name = name[len("schema:"):]
        if name:
            clean.append(name)
    return clean


def _classify_entity(types: list[str]) -> tuple[str, str] | None:
    """
    Classify entity type.
    Returns (category, matched_type) where category is 'Organization', 'LocalBusiness', or 'Person'.
    Returns None if not an entity block.
    """
    for t in types:
        if (
            t in LOCAL_BUSINESS_TYPES
            or t.endswith("Business")
            or t.endswith("Store")
            or t.endswith("Restaurant")
        ):
            return ("LocalBusiness", t)
    for t in types:
        if (
            t in ORGANIZATION_TYPES
            or t.endswith("Organization")
            or t.endswith("Corporation")
        ):
            return ("Organization", t)
    for t in types:
        if t in PERSON_TYPES or t.endswith("Person"):
            return ("Person", t)
    return None


def _flatten_blocks(blocks: Any, seen: Optional[set[int]] = None) -> list[dict]:
    """Flatten nested JSON-LD structures, lists, @graph arrays, and nested entities."""
    if seen is None:
        seen = set()

    flat: list[dict] = []
    if isinstance(blocks, dict):
        obj_id = id(blocks)
        if obj_id in seen:
            return flat
        seen.add(obj_id)

        if "@graph" in blocks and isinstance(blocks["@graph"], list):
            for sub in blocks["@graph"]:
                flat.extend(_flatten_blocks(sub, seen))
        else:
            flat.append(blocks)
            # Traverse nested entity properties
            nested_keys = (
                "publisher",
                "author",
                "creator",
                "organizer",
                "parentOrganization",
                "subOrganization",
                "member",
                "founder",
                "mainEntity",
            )
            for key in nested_keys:
                sub_val = blocks.get(key)
                if isinstance(sub_val, (dict, list)):
                    flat.extend(_flatten_blocks(sub_val, seen))
    elif isinstance(blocks, list):
        for item in blocks:
            flat.extend(_flatten_blocks(item, seen))
    return flat


# ── Public API ───────────────────────────────────────────────────────────────


def audit_entities(
    page_url: str,
    html: str = "",
    json_ld_blocks: list[dict] | None = None,
) -> EntityAuditResult:
    """
    Audit JSON-LD blocks for entity verification (Organization, LocalBusiness, Person).

    Evaluates entity naming, sameAs linkage completeness, and Wikidata/Wikipedia authority connections.
    Boundary: Entity links only — no network requests, no URL validation.

    Args:
        page_url: The URL of the audited page.
        html: Raw HTML content (optional).
        json_ld_blocks: Extracted JSON-LD dictionary blocks.

    Returns:
        EntityAuditResult containing issues and detected entities.
    """
    if json_ld_blocks is None:
        json_ld_blocks = []

    issues: list[EntityIssue] = []
    entities_found: list[dict] = []

    # Flatten and extract all JSON-LD blocks including @graph and nested entities
    all_blocks = _flatten_blocks(json_ld_blocks)

    for block in all_blocks:
        if not isinstance(block, dict):
            continue

        types = _extract_types(block)
        classification = _classify_entity(types)
        if classification is None:
            continue

        category, matched_type = classification
        name = _extract_name(block.get("name"))
        same_as_list = _extract_same_as(block.get("sameAs"))
        same_as_count = len(same_as_list)

        # 1. Check entity name
        if not name:
            issues.append(
                EntityIssue(
                    severity="error",
                    code="ENTITY_NAME_MISSING",
                    message=f"{matched_type} schema has no name field",
                )
            )

        # 2. Check sameAs links
        entity_name_display = f"'{name}'" if name else f"({matched_type})"

        if category in ("Organization", "LocalBusiness"):
            if same_as_count == 0:
                issues.append(
                    EntityIssue(
                        severity="warning",
                        code="SAMEAS_MISSING",
                        message=f"{matched_type} schema {entity_name_display} has no sameAs links",
                    )
                )
            else:
                if same_as_count < 3:
                    issues.append(
                        EntityIssue(
                            severity="info",
                            code="SAMEAS_INCOMPLETE",
                            message=(
                                f"{matched_type} schema {entity_name_display} sameAs has "
                                f"fewer than 3 entries ({same_as_count} found)"
                            ),
                        )
                    )
                has_wikidata = any(
                    "wikidata.org" in url.lower() or "wikipedia.org" in url.lower()
                    for url in same_as_list
                )
                if not has_wikidata:
                    issues.append(
                        EntityIssue(
                            severity="warning",
                            code="WIKIDATA_MISSING",
                            message=(
                                f"{matched_type} schema {entity_name_display} has no "
                                "Wikidata or Wikipedia link in sameAs"
                            ),
                        )
                    )
        elif category == "Person":
            if same_as_count > 0:
                if same_as_count < 3:
                    issues.append(
                        EntityIssue(
                            severity="info",
                            code="SAMEAS_INCOMPLETE",
                            message=(
                                f"Person schema {entity_name_display} sameAs has "
                                f"fewer than 3 entries ({same_as_count} found)"
                            ),
                        )
                    )
                has_wikidata = any(
                    "wikidata.org" in url.lower() or "wikipedia.org" in url.lower()
                    for url in same_as_list
                )
                if not has_wikidata:
                    issues.append(
                        EntityIssue(
                            severity="warning",
                            code="WIKIDATA_MISSING",
                            message=(
                                f"Person schema {entity_name_display} has no "
                                "Wikidata or Wikipedia link in sameAs"
                            ),
                        )
                    )

        # 3. Record found entity
        entities_found.append({
            "type": matched_type,
            "name": name,
            "sameAs_count": same_as_count,
        })

    # If no entity-type blocks found, emit ENTITY_OK with note
    if not entities_found:
        issues.append(
            EntityIssue(
                severity="info",
                code="ENTITY_OK",
                message="No entity schema (Organization, LocalBusiness, Person) found on page",
            )
        )
    elif not issues:
        issues.append(
            EntityIssue(
                severity="info",
                code="ENTITY_OK",
                message=f"Entity verification passed for {len(entities_found)} entity/entities",
            )
        )

    passed = not any(i.severity == "error" for i in issues)

    return EntityAuditResult(
        url=page_url,
        passed=passed,
        issues=issues,
        entities_found=entities_found,
    )


def format_entity_report(result: EntityAuditResult) -> str:
    """Format a human-readable text report from an EntityAuditResult."""
    lines = [
        f"Entity Verification Report for: {result.url}",
        "=" * 60,
        f"Entities Found: {len(result.entities_found)} | Passed: {'Yes' if result.passed else 'No'}",
        f"Issues ({len(result.issues)} total: {result.error_count} errors, {result.warning_count} warnings):\n",
    ]
    icon_map = {"error": "✗", "warning": "⚠", "info": "ℹ"}
    for issue in result.issues:
        icon = icon_map.get(issue.severity, "?")
        lines.append(f"  {icon} [{issue.code}] {issue.message}")

    if result.entities_found:
        lines.append("\nEntities Detected:")
        for ent in result.entities_found:
            lines.append(f"  - {ent['type']}: '{ent['name']}' ({ent['sameAs_count']} sameAs links)")

    return "\n".join(lines)
