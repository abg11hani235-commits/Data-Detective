import re
from typing import Any, Dict, List, Set, Tuple


class FindingsValidator:
    """
    Validates that numerical claims in LLM-synthesized findings are grounded
    in actual numbers present in the sandboxed execution results (metrics, tables, metadata).
    Prevents fabricated metrics from being presented as verified facts.
    """

    @classmethod
    def extract_numbers_from_text(cls, text: str) -> List[float]:
        """Extracts numerical sequences (integers, floats, percentages, currency) from text."""
        # Clean currency symbols and commas, e.g. $142,500.50 -> 142500.50
        cleaned = re.sub(r"[,$€£]", "", text)
        matches = re.findall(r"[-+]?\b\d+(?:\.\d+)?\b", cleaned)
        numbers = []
        for m in matches:
            try:
                numbers.append(float(m))
            except ValueError:
                pass
        return numbers

    @classmethod
    def collect_verified_numbers(
        cls,
        metrics: Dict[str, Any],
        tables: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> Set[float]:
        """Gathers all legitimate numbers computed by the sandbox or present in metadata."""
        verified = set()

        # From metrics
        for v in metrics.values():
            if isinstance(v, (int, float)):
                verified.add(round(float(v), 2))
                verified.add(round(float(v), 0))
            elif isinstance(v, str):
                for n in cls.extract_numbers_from_text(v):
                    verified.add(round(n, 2))
                    verified.add(round(n, 0))

        # From tables
        for tbl in tables:
            data = tbl.get("data", []) or tbl.get("rows", [])
            for row in data:
                if isinstance(row, dict):
                    vals = row.values()
                elif isinstance(row, (list, tuple)):
                    vals = row
                else:
                    vals = [row]
                for v in vals:
                    if isinstance(v, (int, float)):
                        verified.add(round(float(v), 2))
                        verified.add(round(float(v), 0))
                    elif isinstance(v, str):
                        for n in cls.extract_numbers_from_text(v):
                            verified.add(round(n, 2))
                            verified.add(round(n, 0))

        # From metadata
        for k in ["row_count", "column_count"]:
            if k in metadata and isinstance(metadata[k], (int, float)):
                verified.add(float(metadata[k]))

        return verified

    @classmethod
    def is_number_grounded(cls, num: float, verified_numbers: Set[float], tolerance: float = 0.5) -> bool:
        """Checks if a number is close to any verified computed number."""
        # Ignore trivial integers like 1, 2, 3 (e.g. 'top 3', 'step 1')
        if num in [1.0, 2.0, 3.0, 4.0, 5.0, 10.0]:
            return True

        for v in verified_numbers:
            if abs(num - v) <= tolerance:
                return True
            # Also check if num is percentage representation (e.g. 0.405 vs 40.5%)
            if abs(num - (v * 100)) <= tolerance or abs((num * 100) - v) <= tolerance:
                return True

        return False

    @classmethod
    def verify_findings(
        cls,
        findings: List[str],
        metrics: Dict[str, Any],
        tables: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> Tuple[List[str], List[str]]:
        """
        Filters findings: verified findings are retained.
        Findings asserting unverified/fabricated numbers are stripped or flagged,
        and added to caveats.
        """
        verified_numbers = cls.collect_verified_numbers(metrics, tables, metadata)
        approved_findings: List[str] = []
        unverified_caveats: List[str] = []

        for finding in findings:
            finding_numbers = cls.extract_numbers_from_text(finding)
            has_unverified = False
            unverified_val = None

            for num in finding_numbers:
                if not cls.is_number_grounded(num, verified_numbers):
                    has_unverified = True
                    unverified_val = num
                    break

            if has_unverified:
                unverified_caveats.append(
                    f"A proposed claim referencing {unverified_val} was flagged and excluded because {unverified_val} does not appear in computed results."
                )
            else:
                approved_findings.append(finding)

        return approved_findings, unverified_caveats
