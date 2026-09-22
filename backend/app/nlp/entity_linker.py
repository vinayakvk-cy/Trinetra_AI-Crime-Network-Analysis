"""
TRINETRA Entity Linker
======================

Links extracted entity candidates to existing entities.

Responsibilities
----------------
- Normalize entity values
- Compare extracted entities with known entities
- Generate candidate matches
- Calculate similarity/confidence
- Support exact and fuzzy matching
- Preserve ambiguous matches for later review

This module does NOT:
- declare two people to be the same person with certainty
- determine guilt or innocence
- assign criminal risk
- create Neo4j nodes
- create Neo4j relationships

The graph layer can consume the confirmed/approved links later.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from typing import Any, Iterable

from app.nlp.entity_extractor import (
    EntityCandidate,
)


# ============================================================
# MATCH TYPES
# ============================================================

EXACT_MATCH = "EXACT_MATCH"
NORMALIZED_MATCH = "NORMALIZED_MATCH"
FUZZY_MATCH = "FUZZY_MATCH"
NO_MATCH = "NO_MATCH"
AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"


SUPPORTED_MATCH_TYPES = {
    EXACT_MATCH,
    NORMALIZED_MATCH,
    FUZZY_MATCH,
    NO_MATCH,
    AMBIGUOUS_MATCH,
}


# ============================================================
# LINKED ENTITY
# ============================================================


@dataclass
class KnownEntity:
    """
    Represents an existing entity in the system.

    This class is intentionally independent from the database
    ORM models. The linker can therefore be used before the
    database/graph layer is involved.
    """

    entity_id: str

    entity_type: str

    value: str

    aliases: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def all_values(self) -> list[str]:
        """
        Return the primary value plus aliases.
        """

        values = [self.value]

        values.extend(
            self.aliases
        )

        return values


# ============================================================
# LINK CANDIDATE
# ============================================================


@dataclass
class LinkCandidate:
    """
    Candidate match between an extracted entity and an
    existing entity.
    """

    extracted_entity: EntityCandidate

    known_entity: KnownEntity | None

    match_type: str

    score: float

    matched_value: str | None = None

    reasons: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert candidate to dictionary.
        """

        return {
            "extracted_entity": (
                self.extracted_entity.to_dict()
            ),
            "known_entity": (
                asdict(self.known_entity)
                if self.known_entity
                else None
            ),
            "match_type": self.match_type,
            "score": self.score,
            "matched_value": self.matched_value,
            "reasons": self.reasons,
            "metadata": self.metadata,
        }


# ============================================================
# LINK RESULT
# ============================================================


@dataclass
class EntityLinkResult:
    """
    Result of linking one extracted entity.
    """

    extracted_entity: EntityCandidate

    best_match: LinkCandidate | None

    candidates: list[LinkCandidate] = field(
        default_factory=list
    )

    linked: bool = False

    ambiguous: bool = False

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert result to dictionary.
        """

        return {
            "extracted_entity": (
                self.extracted_entity.to_dict()
            ),
            "best_match": (
                self.best_match.to_dict()
                if self.best_match
                else None
            ),
            "candidates": [
                candidate.to_dict()
                for candidate in self.candidates
            ],
            "linked": self.linked,
            "ambiguous": self.ambiguous,
            "metadata": self.metadata,
        }


# ============================================================
# LINKER
# ============================================================


class EntityLinker:
    """
    Entity linking engine.

    Matching strategy:

        1. Exact match
        2. Normalized match
        3. Alias match
        4. Fuzzy match
        5. Ambiguity detection

    The linker is intentionally conservative.
    """

    def __init__(
        self,
        fuzzy_threshold: float = 0.85,
        link_threshold: float = 0.90,
        ambiguity_margin: float = 0.05,
    ) -> None:

        self.fuzzy_threshold = max(
            0.0,
            min(1.0, fuzzy_threshold),
        )

        self.link_threshold = max(
            0.0,
            min(1.0, link_threshold),
        )

        self.ambiguity_margin = max(
            0.0,
            ambiguity_margin,
        )

    # ========================================================
    # SINGLE ENTITY
    # ========================================================

    def link(
        self,
        entity: EntityCandidate,
        known_entities: Iterable[KnownEntity],
    ) -> EntityLinkResult:
        """
        Link one extracted entity against known entities.
        """

        known_entities = list(
            known_entities
        )

        candidates: list[
            LinkCandidate
        ] = []

        for known_entity in known_entities:

            # Entity types must match.
            if (
                entity.entity_type
                != known_entity.entity_type
            ):
                continue

            candidate = (
                self._compare_entity(
                    entity,
                    known_entity,
                )
            )

            if candidate:

                candidates.append(
                    candidate
                )

        candidates.sort(
            key=lambda candidate:
                candidate.score,
            reverse=True,
        )

        if not candidates:

            return EntityLinkResult(
                extracted_entity=entity,
                best_match=None,
                candidates=[],
                linked=False,
                ambiguous=False,
            )

        best = candidates[0]

        ambiguous = self._is_ambiguous(
            candidates
        )

        linked = (
            best.score
            >= self.link_threshold
            and not ambiguous
        )

        if ambiguous:

            best.match_type = (
                AMBIGUOUS_MATCH
            )

        return EntityLinkResult(
            extracted_entity=entity,
            best_match=best,
            candidates=candidates,
            linked=linked,
            ambiguous=ambiguous,
            metadata={
                "link_threshold": (
                    self.link_threshold
                ),
                "fuzzy_threshold": (
                    self.fuzzy_threshold
                ),
            },
        )

    # ========================================================
    # MULTIPLE ENTITIES
    # ========================================================

    def link_many(
        self,
        entities: Iterable[EntityCandidate],
        known_entities: Iterable[KnownEntity],
    ) -> list[EntityLinkResult]:
        """
        Link multiple extracted entities.
        """

        known_entities = list(
            known_entities
        )

        results: list[
            EntityLinkResult
        ] = []

        for entity in entities:

            results.append(
                self.link(
                    entity,
                    known_entities,
                )
            )

        return results

    # ========================================================
    # COMPARISON
    # ========================================================

    def _compare_entity(
        self,
        extracted: EntityCandidate,
        known: KnownEntity,
    ) -> LinkCandidate | None:
        """
        Compare one extracted entity against one known entity.
        """

        extracted_value = (
            extracted.value.strip()
        )

        # ----------------------------------------------------
        # Primary value
        # ----------------------------------------------------

        values = known.all_values()

        best_score = 0.0

        best_value: str | None = None

        best_type = NO_MATCH

        reasons: list[str] = []

        for known_value in values:

            score, match_type, reason = (
                self._compare_values(
                    extracted.entity_type,
                    extracted_value,
                    known_value,
                )
            )

            if score > best_score:

                best_score = score

                best_value = known_value

                best_type = match_type

                reasons = [reason]

        if best_score <= 0:
            return None

        if best_score < self.fuzzy_threshold:

            return LinkCandidate(
                extracted_entity=extracted,
                known_entity=known,
                match_type=best_type,
                score=best_score,
                matched_value=best_value,
                reasons=reasons,
            )

        return LinkCandidate(
            extracted_entity=extracted,
            known_entity=known,
            match_type=best_type,
            score=best_score,
            matched_value=best_value,
            reasons=reasons,
        )

    # ========================================================
    # VALUE COMPARISON
    # ========================================================

    def _compare_values(
        self,
        entity_type: str,
        extracted_value: str,
        known_value: str,
    ) -> tuple[
        float,
        str,
        str,
    ]:
        """
        Compare two values.
        """

        if not extracted_value or not known_value:

            return (
                0.0,
                NO_MATCH,
                "Empty value",
            )

        # ----------------------------------------------------
        # Exact
        # ----------------------------------------------------

        if extracted_value == known_value:

            return (
                1.0,
                EXACT_MATCH,
                "Exact value match",
            )

        # ----------------------------------------------------
        # Case-insensitive exact
        # ----------------------------------------------------

        if (
            extracted_value.lower()
            == known_value.lower()
        ):

            return (
                0.98,
                NORMALIZED_MATCH,
                "Case-insensitive match",
            )

        # ----------------------------------------------------
        # Type-specific normalization
        # ----------------------------------------------------

        normalized_extracted = (
            self._normalize_for_type(
                entity_type,
                extracted_value,
            )
        )

        normalized_known = (
            self._normalize_for_type(
                entity_type,
                known_value,
            )
        )

        if (
            normalized_extracted
            and normalized_extracted
            == normalized_known
        ):

            return (
                0.96,
                NORMALIZED_MATCH,
                "Normalized value match",
            )

        # ----------------------------------------------------
        # Fuzzy comparison
        # ----------------------------------------------------

        similarity = (
            SequenceMatcher(
                None,
                normalized_extracted,
                normalized_known,
            ).ratio()
        )

        if similarity >= self.fuzzy_threshold:

            return (
                similarity,
                FUZZY_MATCH,
                "Fuzzy similarity match",
            )

        return (
            similarity,
            NO_MATCH,
            "Below fuzzy threshold",
        )

    # ========================================================
    # TYPE NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_for_type(
        entity_type: str,
        value: str,
    ) -> str:
        """
        Normalize values according to entity type.
        """

        value = value.strip()

        # ----------------------------------------------------
        # Phone
        # ----------------------------------------------------

        if entity_type == "PHONE":

            return re.sub(
                r"\D",
                "",
                value,
            )

        # ----------------------------------------------------
        # Email
        # ----------------------------------------------------

        if entity_type == "EMAIL":

            return value.lower()

        # ----------------------------------------------------
        # Identifiers
        # ----------------------------------------------------

        if entity_type in {
            "CASE",
            "FIR",
            "EVIDENCE",
            "DEVICE",
            "INMATE",
        }:

            value = value.upper()

            return re.sub(
                r"[\s\-_/:]+",
                "",
                value,
            )

        # ----------------------------------------------------
        # Person
        # ----------------------------------------------------

        if entity_type == "PERSON":

            value = value.lower()

            value = re.sub(
                r"[^a-z0-9\s]",
                "",
                value,
            )

            value = re.sub(
                r"\s+",
                " ",
                value,
            )

            return value.strip()

        # ----------------------------------------------------
        # Default
        # ----------------------------------------------------

        value = value.lower()

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    # ========================================================
    # AMBIGUITY
    # ========================================================

    def _is_ambiguous(
        self,
        candidates: list[LinkCandidate],
    ) -> bool:
        """
        Determine whether multiple candidates are too close
        in score to safely select one.
        """

        if len(candidates) < 2:
            return False

        first = candidates[0]
        second = candidates[1]

        if (
            first.score < self.link_threshold
        ):
            return False

        return (
            first.score - second.score
            <= self.ambiguity_margin
        )

    # ========================================================
    # BEST MATCH
    # ========================================================

    @staticmethod
    def best_match(
        result: EntityLinkResult,
    ) -> KnownEntity | None:
        """
        Return the best known entity only when the result
        is sufficiently confident and non-ambiguous.
        """

        if not result.linked:
            return None

        if result.best_match is None:
            return None

        return result.best_match.known_entity


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================


def link_entity(
    entity: EntityCandidate,
    known_entities: Iterable[KnownEntity],
) -> EntityLinkResult:
    """
    Convenience function for linking one entity.
    """

    linker = EntityLinker()

    return linker.link(
        entity,
        known_entities,
    )


def link_entities(
    entities: Iterable[EntityCandidate],
    known_entities: Iterable[KnownEntity],
) -> list[EntityLinkResult]:
    """
    Convenience function for linking multiple entities.
    """

    linker = EntityLinker()

    return linker.link_many(
        entities,
        known_entities,
    )