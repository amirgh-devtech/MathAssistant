# myLab/module/smart_lab_loader.py
"""
PhET Smart Lab Loader v12.0 - Ultra-Fast Direct File Access
Reads HTML files directly from build/ directory.
Zero dependencies beyond Python stdlib.
"""
from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Optional, List, Dict, Union, TypedDict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

FILENAME_PATTERN = re.compile(r'''
    ^
    ([a-z0-9]+(?:-[a-z0-9]+)*)
    _
    (G7|G8|G9|G10|G11|G12|ACA)
    -
    (MATH|PHYS|CHEM|BIO)
    \.html$
''', re.VERBOSE)

MIN_EXPECTED_LABS = 90


class Grade:
    G7, G8, G9, G10, G11, G12, ACA = "G7", "G8", "G9", "G10", "G11", "G12", "ACA"
    ALL = frozenset({G7, G8, G9, G10, G11, G12, ACA})
    LABELS = {
        G7: "پایه هفتم", G8: "پایه هشتم", G9: "پایه نهم",
        G10: "پایه دهم", G11: "پایه یازدهم", G12: "پایه دوازدهم",
        ACA: "دانشگاهی"
    }


class Subject:
    MATH, PHYS, CHEM, BIO = "MATH", "PHYS", "CHEM", "BIO"
    ALL = frozenset({MATH, PHYS, CHEM, BIO})
    LABELS = {
        MATH: "ریاضی", PHYS: "فیزیک", CHEM: "شیمی", BIO: "زیست"
    }


@dataclass(frozen=True, slots=True)
class LabInfo:
    key: str
    sim_name: str
    grade: str
    subject: str
    filename: str


class LoaderStats(TypedDict, total=False):
    total_labs: int
    cached_labs: int
    build_dir: str


class SmartPhETLoader:
    """
    Ultra-fast PhET simulation loader.
    Reads HTML files directly from build/ directory.

    Usage:
        loader = SmartPhETLoader("path/to/build")
        html = loader.get_lab("ohms-law", Grade.G8, Subject.PHYS)
    """

    __slots__ = ('_build_dir', '_index', '_cache')

    def __init__(self, build_dir: Union[str, Path]):
        self._build_dir = Path(build_dir)
        self._index: Dict[str, LabInfo] = {}
        self._cache: Dict[str, str] = {}
        self._build_index()

        logger.info(
            "SmartPhETLoader ready | build=%s | labs=%d",
            self._build_dir, len(self._index)
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    @property
    def total_labs(self) -> int:
        return len(self._index)

    @property
    def grade_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for info in self._index.values():
            counts[info.grade] = counts.get(info.grade, 0) + 1
        return dict(sorted(counts.items()))

    @property
    def subject_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for info in self._index.values():
            counts[info.subject] = counts.get(info.subject, 0) + 1
        return dict(sorted(counts.items()))

    def _build_index(self):
        """Scan build/ directory for HTML files."""
        if not self._build_dir.exists():
            logger.error("Build directory not found: %s", self._build_dir)
            return

        for html_file in self._build_dir.glob("*.html"):
            match = FILENAME_PATTERN.match(html_file.name)
            if match:
                sim_name, grade, subject = match.groups()
                key = f"{sim_name}_{grade}-{subject}"
                self._index[key] = LabInfo(
                    key=key, sim_name=sim_name,
                    grade=grade, subject=subject,
                    filename=html_file.name
                )

        logger.debug("Indexed %d labs", len(self._index))

    @staticmethod
    def _validate_grade(grade: str):
        if grade not in Grade.ALL:
            raise ValueError(f"Invalid grade '{grade}'. Valid: {', '.join(sorted(Grade.ALL))}")

    @staticmethod
    def _validate_subject(subject: str):
        if subject not in Subject.ALL:
            raise ValueError(f"Invalid subject '{subject}'. Valid: {', '.join(sorted(Subject.ALL))}")

    def list_labs(self, grade: Optional[str] = None, subject: Optional[str] = None) -> List[LabInfo]:
        if grade is not None:
            self._validate_grade(grade)
        if subject is not None:
            self._validate_subject(subject)

        labs = [
            info for info in self._index.values()
            if (grade is None or info.grade == grade) and
               (subject is None or info.subject == subject)
        ]
        return sorted(labs, key=lambda x: x.sim_name)

    def get_lab(self, sim_name: str, grade: str, subject: str) -> Optional[str]:
        """Load HTML content (sub-millisecond from cache)."""
        self._validate_grade(grade)
        self._validate_subject(subject)

        key = f"{sim_name}_{grade}-{subject}"

        if key in self._cache:
            return self._cache[key]

        info = self._index.get(key)
        if not info:
            logger.warning("Lab not found: %s", key)
            return None

        file_path = self._build_dir / info.filename
        try:
            html = file_path.read_text('utf-8')
            self._cache[key] = html
            return html
        except Exception as e:
            logger.error("Failed to read %s: %s", file_path, e)
            return None

    def search(self, query: str) -> List[LabInfo]:
        q = query.lower().strip()
        if not q:
            return []
        return sorted(
            [info for info in self._index.values() if q in info.sim_name.lower()],
            key=lambda x: x.sim_name
        )

    def get_stats(self) -> LoaderStats:
        return {
            "total_labs": self.total_labs,
            "cached_labs": len(self._cache),
            "build_dir": str(self._build_dir),
        }


def create_loader(build_dir: Optional[Union[str, Path]] = None) -> SmartPhETLoader:
    if build_dir:
        path = Path(build_dir)
    else:
        path = Path(__file__).resolve().parent.parent / "build"
    return SmartPhETLoader(path)
