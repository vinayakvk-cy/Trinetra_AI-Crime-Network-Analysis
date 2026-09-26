"""
Unit tests for TRINETRA Entity Extractor.
Tests detection of PERSON, ORGANIZATION, PHONE, FIR, and CASE entities.
"""

from app.nlp.entity_extractor import (
    EntityExtractor,
    PERSON,
    ORGANIZATION,
    PHONE,
    FIR,
    CASE,
)


def get_entities_by_type(entities, entity_type):
    """Helper to get list of extracted entity values for a given type."""
    return [e.value for e in entities if e.entity_type == entity_type]


def test_extract_person_and_organization():
    extractor = EntityExtractor()
    text = "Arjun Rao met with representatives from Apex Logistics Pvt Ltd."
    result = extractor.extract(text)

    persons = get_entities_by_type(result.entities, PERSON)
    orgs = get_entities_by_type(result.entities, ORGANIZATION)

    assert "Arjun Rao" in persons
    assert "Apex Logistics Pvt Ltd" in orgs


def test_extract_phone_number():
    extractor = EntityExtractor()
    text = "Suspect contacted primary line at +91 98765 43210 during the incident."
    result = extractor.extract(text)

    phones = get_entities_by_type(result.entities, PHONE)
    assert any("98765" in p for p in phones)


def test_extract_case_and_fir():
    extractor = EntityExtractor()
    text = "Referencing Case Number: CASE-2024-009 linked to FIR-402/2024."
    result = extractor.extract(text)

    cases = get_entities_by_type(result.entities, CASE)
    firs = get_entities_by_type(result.entities, FIR)

    assert any("CASE-2024-009" in c for c in cases)
    assert any("402" in f for f in firs)
