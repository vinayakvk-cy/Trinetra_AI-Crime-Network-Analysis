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
    PENAL_SECTION,
    VEHICLE,
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

def test_extract_penal_sections():
    extractor = EntityExtractor()
    text = "Suspect was charged under IPC 420, Section 120B IPC and BNS Section 316."
    result = extractor.extract(text)

    sections = get_entities_by_type(result.entities, PENAL_SECTION)
    assert any("420" in s for s in sections)
    assert any("120B" in s or "120b" in s.lower() for s in sections)
    assert any("316" in s for s in sections)


def test_extract_vehicle_registration():
    extractor = EntityExtractor()
    text = "Getaway car with plate DL 01 AB 1234 was seen near truck MH-12-CD-5678."
    result = extractor.extract(text)

    vehicles = get_entities_by_type(result.entities, VEHICLE)
    assert any("DL 01 AB 1234" in v for v in vehicles)
    assert any("MH-12-CD-5678" in v for v in vehicles)

