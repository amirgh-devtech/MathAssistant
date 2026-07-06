# myLab/api/__init__.py
"""
PhET Lab API - Bridge between MathAssistant and PhET simulations.

Exports:
    PhETLabAPI  - High-level API for lab data access
    LabManager  - CEFPython-based lab display manager
    Grade       - Grade constants (G7, G8, G9, G10, G11, G12, ACA)
    Subject     - Subject constants (MATH, PHYS, CHEM, BIO)
    LabInfo     - Lab metadata dataclass
"""
import sys
from pathlib import Path

# Ensure myLab is importable when used from outside
_myLab_dir = Path(__file__).resolve().parent.parent
if str(_myLab_dir) not in sys.path:
    sys.path.insert(0, str(_myLab_dir))

from module.smart_lab_loader import SmartPhETLoader, Grade, Subject, LabInfo


class LabAPI:
    """
    High-level API for accessing lab data.

    Provides lab listing, searching, and content loading.
    Used by LabManager and directly by MathAssistant UI.

    Usage:
        api = PhETLabAPI()
        html = api.get_lab("ohms-law", "G8", "PHYS")
        labs = api.list_labs(grade="G9", subject="PHYS")
        tree = api.get_tree()
    """

    def __init__(self, build_dir: str = None):
        """
        Initialize the API.

        Args:
            build_dir: Path to build/ directory with HTML files.
                       Defaults to myLab/build/ relative to this file.
        """
        if build_dir is None:
            build_dir = Path(__file__).resolve().parent.parent / "build"
        self._loader = SmartPhETLoader(build_dir)

    # ---- Lab Access ----

    def get_lab(self, sim_name: str, grade: str, subject: str) -> str | None:
        """
        Get HTML content of a specific lab.

        Args:
            sim_name: Simulation name (e.g., "ohms-law")
            grade: Grade code (e.g., "G8")
            subject: Subject code (e.g., "PHYS")

        Returns:
            HTML string or None if not found.
        """
        return self._loader.get_lab(sim_name, grade, subject)

    def list_labs(self, grade: str = None, subject: str = None) -> list[dict]:
        """
        List available labs with optional filtering.

        Args:
            grade: Filter by grade (None = all)
            subject: Filter by subject (None = all)

        Returns:
            List of dicts with keys: key, name, grade, grade_label, subject, subject_label
        """
        labs = self._loader.list_labs(grade=grade, subject=subject)
        return [
            {
                "key": lab.key,
                "name": lab.sim_name,
                "grade": lab.grade,
                "grade_label": Grade.LABELS.get(lab.grade, lab.grade),
                "subject": lab.subject,
                "subject_label": Subject.LABELS.get(lab.subject, lab.subject),
            }
            for lab in labs
        ]

    def search(self, query: str) -> list[dict]:
        """
        Search labs by name (case-insensitive partial match).

        Args:
            query: Search term

        Returns:
            List of dicts matching the query.
        """
        labs = self._loader.search(query)
        return [
            {
                "key": lab.key,
                "name": lab.sim_name,
                "grade": lab.grade,
                "grade_label": Grade.LABELS.get(lab.grade, lab.grade),
                "subject": lab.subject,
                "subject_label": Subject.LABELS.get(lab.subject, lab.subject),
            }
            for lab in labs
        ]

    # ---- Grade/Subject Info ----

    @staticmethod
    def get_grades() -> list[dict]:
        """Get list of all grades with labels."""
        return [
            {"code": g, "label": Grade.LABELS[g]}
            for g in [Grade.G7, Grade.G8, Grade.G9, Grade.G10, Grade.G11, Grade.G12, Grade.ACA]
        ]

    @staticmethod
    def get_subjects() -> list[dict]:
        """Get list of all subjects with labels."""
        return [
            {"code": s, "label": Subject.LABELS[s]}
            for s in [Subject.MATH, Subject.PHYS, Subject.CHEM, Subject.BIO]
        ]

    # ---- Statistics ----

    def get_stats(self) -> dict:
        """Get loader statistics."""
        return {
            "total_labs": self._loader.total_labs,
            "grade_counts": self._loader.grade_counts,
            "subject_counts": self._loader.subject_counts,
        }

    def get_tree(self) -> dict:
        """
        Get full hierarchical tree for UI navigation.

        Structure:
        {
            "G7": {
                "label": "پایه هفتم",
                "subjects": {
                    "MATH": {
                        "label": "ریاضی",
                        "labs": [
                            {"key": "...", "name": "...", ...},
                            ...
                        ]
                    },
                    ...
                }
            },
            ...
        }
        """
        tree = {}
        grade_order = [Grade.G7, Grade.G8, Grade.G9, Grade.G10, Grade.G11, Grade.G12, Grade.ACA]
        subject_order = [Subject.MATH, Subject.PHYS, Subject.CHEM, Subject.BIO]

        for grade in grade_order:
            grade_labs = {}
            for subject in subject_order:
                labs = self.list_labs(grade=grade, subject=subject)
                if labs:
                    grade_labs[subject] = {
                        "label": Subject.LABELS[subject],
                        "labs": labs
                    }
            if grade_labs:
                tree[grade] = {
                    "label": Grade.LABELS[grade],
                    "subjects": grade_labs
                }
        return tree

    @property
    def total_labs(self) -> int:
        return self._loader.total_labs
