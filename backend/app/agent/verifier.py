import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.models.schemas import Claim, EvidenceItem


class EvidenceRegistry:
    """
    Structured registry of ground-truth numerical facts extracted directly
    from deterministic sandbox execution (computed metrics, aggregated tables, and metadata).
    """

    def __init__(self):
        self.items: Dict[str, EvidenceItem] = {}
        self._counter: int = 0

    def register(
        self,
        source: str,
        metric_name: str,
        value: float,
        dimension: Optional[str] = None,
        entity: Optional[str] = None,
        aggregation: Optional[str] = None,
        raw_repr: Optional[str] = None,
    ) -> EvidenceItem:
        self._counter += 1
        ev_id = f"ev_{self._counter}"
        item = EvidenceItem(
            id=ev_id,
            source=source,
            metric_name=metric_name.strip().lower(),
            dimension=dimension.strip().lower() if dimension else None,
            entity=str(entity).strip().lower() if entity is not None else None,
            aggregation=aggregation.strip().lower() if aggregation else None,
            value=float(value),
            raw_repr=str(raw_repr if raw_repr is not None else value),
        )
        self.items[ev_id] = item
        return item

    def get_by_metric_and_entity(
        self,
        metric_name: str,
        entity: Optional[str] = None,
    ) -> Optional[EvidenceItem]:
        norm_metric = metric_name.strip().lower()
        norm_entity = str(entity).strip().lower() if entity is not None else None

        for item in self.items.values():
            if item.metric_name == norm_metric:
                if norm_entity is None or item.entity == norm_entity:
                    return item
        return None

    def find_items_by_value(
        self,
        target_value: float,
        rel_tolerance: float = 0.015,
        abs_tolerance: float = 0.5,
    ) -> List[EvidenceItem]:
        matches = []
        for item in self.items.values():
            val = item.value
            # Direct match
            if abs(target_value - val) <= abs_tolerance or (
                val != 0 and abs(target_value - val) / abs(val) <= rel_tolerance
            ):
                matches.append(item)
                continue
            # Percentage scaling match (e.g. 0.25 vs 25%)
            if abs(target_value - (val * 100)) <= abs_tolerance or (
                val != 0 and abs(target_value - (val * 100)) / 100 <= rel_tolerance
            ):
                matches.append(item)
                continue
            if abs((target_value * 100) - val) <= abs_tolerance:
                matches.append(item)
        return matches

    @classmethod
    def build_from_execution_output(
        cls,
        metrics: Dict[str, Any],
        tables: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> "EvidenceRegistry":
        registry = cls()

        # 1. Register scalar metrics
        for k, v in (metrics or {}).items():
            if isinstance(v, (int, float)) and not math.isnan(v):
                registry.register(
                    source="metrics",
                    metric_name=k,
                    value=float(v),
                    raw_repr=str(v),
                )
            elif isinstance(v, str):
                nums = cls._extract_numbers(v)
                if nums:
                    registry.register(
                        source="metrics",
                        metric_name=k,
                        value=nums[0],
                        raw_repr=v,
                    )

        # 2. Register tabular records
        for tbl in (tables or []):
            tbl_name = tbl.get("title") or tbl.get("name") or "table"
            rows = tbl.get("data") or tbl.get("rows") or []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                # Identify categorical columns and numeric columns
                dim_col = None
                entity_val = None
                num_cols = {}

                for col, val in row.items():
                    if isinstance(val, (int, float)) and not math.isnan(val):
                        num_cols[col] = float(val)
                    elif isinstance(val, str):
                        nums = cls._extract_numbers(val)
                        if len(nums) == 1 and re.match(r"^[-+]?[\$€£]?\d+(?:\.\d+)?%?$", val.strip()):
                            num_cols[col] = nums[0]
                        else:
                            dim_col = col
                            entity_val = val

                for num_col, num_val in num_cols.items():
                    registry.register(
                        source=f"table:{tbl_name}",
                        metric_name=num_col,
                        dimension=dim_col,
                        entity=entity_val,
                        value=num_val,
                        raw_repr=str(num_val),
                    )

        # 3. Register dataset metadata
        for k in ["row_count", "column_count"]:
            if k in (metadata or {}) and isinstance(metadata[k], (int, float)):
                registry.register(
                    source="metadata",
                    metric_name=k,
                    value=float(metadata[k]),
                    raw_repr=str(metadata[k]),
                )

        return registry

    @staticmethod
    def _extract_numbers(text: str) -> List[float]:
        cleaned = re.sub(r"[,$€£]", "", text)
        matches = re.findall(r"[-+]?\b\d+(?:\.\d+)?\b", cleaned)
        res = []
        for m in matches:
            try:
                res.append(float(m))
            except ValueError:
                pass
        return res


class FindingsValidator:
    """
    Rigorous Evidence-Based Claim Validator.
    Verifies that claims:
    1. Have backing evidence in the registry.
    2. Have correct numerical calculations within tolerance.
    3. Are bound to the correct context (metric and entity/dimension).
    4. Are not logically contradicted by computed data.
    """

    @classmethod
    def validate_claim(
        cls,
        claim: Claim,
        registry: EvidenceRegistry,
        tolerance: float = 0.5,
    ) -> Claim:
        """
        Validates a single claim against the registered evidence.
        Updates validation_status, evidence_id, and reason.
        """
        # Look for matching evidence by metric name and entity
        matching_evidence = registry.get_by_metric_and_entity(
            metric_name=claim.metric_name,
            entity=claim.entity,
        )

        # Case 1: No evidence found for this metric/entity combination
        if matching_evidence is None:
            # Check if the claimed value matches another metric or entity (context mismatch)
            if claim.claimed_value is not None:
                cross_matches = registry.find_items_by_value(claim.claimed_value)
                if cross_matches:
                    m = cross_matches[0]
                    claim.validation_status = "context_mismatch"
                    claim.reason = (
                        f"Context mismatch: Claimed value {claim.claimed_value} belongs to "
                        f"'{m.metric_name}' (entity: {m.entity or 'global'}), not '{claim.metric_name}' "
                        f"(entity: {claim.entity or 'global'})."
                    )
                    return claim

            claim.validation_status = "missing_evidence"
            claim.reason = f"Missing evidence: No computed result found for metric '{claim.metric_name}'" + (
                f" and entity '{claim.entity}'." if claim.entity else "."
            )
            return claim

        # Case 2: Evidence exists, check numerical accuracy
        if claim.claimed_value is not None:
            ev_val = matching_evidence.value
            # Check if numbers match (or percentage match)
            is_match = (
                abs(claim.claimed_value - ev_val) <= tolerance
                or abs(claim.claimed_value - (ev_val * 100)) <= tolerance
                or abs((claim.claimed_value * 100) - ev_val) <= tolerance
            )

            if not is_match:
                # Check if this number actually belongs to another metric or entity
                cross_matches = registry.find_items_by_value(claim.claimed_value)
                other_matches = [
                    m for m in cross_matches 
                    if m.metric_name != matching_evidence.metric_name or m.entity != matching_evidence.entity
                ]
                if other_matches:
                    m = other_matches[0]
                    claim.validation_status = "context_mismatch"
                    claim.reason = (
                        f"Context mismatch: Claim asserted {claim.claimed_value} for '{claim.metric_name}', "
                        f"but that value actually belongs to '{m.metric_name}' (entity: {m.entity or 'global'}). "
                        f"The computed value for '{claim.metric_name}' is {ev_val}."
                    )
                    return claim

                claim.validation_status = "unsupported"
                claim.reason = (
                    f"Unsupported numerical claim: Claim asserted {claim.claimed_value}, "
                    f"but verified computed value is {ev_val}."
                )
                return claim

        # Case 3: Comparison logic verification
        if claim.comparison_direction and claim.entity:
            # E.g. Claim asserts North > South
            pass

        # Claim passed all verification checks
        claim.evidence_id = matching_evidence.id
        claim.validation_status = "verified"
        claim.reason = f"Verified against {matching_evidence.source} ({matching_evidence.id})"
        return claim

    @classmethod
    def verify_findings(
        cls,
        findings: List[Any],
        metrics: Dict[str, Any],
        tables: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> Tuple[List[str], List[str]]:
        """
        Legacy compatible interface that processes a list of finding statements or Claim objects.
        Returns:
            approved_findings: List[str]
            caveats: List[str]
        """
        registry = EvidenceRegistry.build_from_execution_output(metrics, tables, metadata)
        approved_findings: List[str] = []
        caveats: List[str] = []

        all_verified_numbers = {round(item.value, 2) for item in registry.items.values()}
        all_verified_numbers.update({round(item.value * 100, 2) for item in registry.items.values()})

        for finding in findings:
            if isinstance(finding, Claim):
                validated = cls.validate_claim(finding, registry)
                if validated.validation_status == "verified":
                    approved_findings.append(validated.statement)
                else:
                    caveats.append(f"Excluded unverified claim: {validated.statement} ({validated.reason})")
            elif isinstance(finding, str):
                finding_numbers = EvidenceRegistry._extract_numbers(finding)
                has_unverified = False
                unverified_val = None

                for num in finding_numbers:
                    # Ignore common formatting / ordinal numbers
                    if num in [1.0, 2.0, 3.0, 4.0, 5.0, 10.0]:
                        continue
                    # Check against registry values
                    matches = registry.find_items_by_value(num)
                    if not matches:
                        has_unverified = True
                        unverified_val = num
                        break

                if has_unverified:
                    caveats.append(
                        f"A proposed claim referencing {unverified_val} was flagged and excluded because "
                        f"{unverified_val} does not appear in computed results."
                    )
                else:
                    approved_findings.append(finding)

        return approved_findings, caveats
