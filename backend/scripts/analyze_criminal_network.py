"""
TRINETRA - Criminal Network Centrality Analyzer
================================================
A standalone investigative CLI tool that parses raw crime dossiers,
extracts entities and criminal ties, builds a network graph, and calculates
key centrality metrics to identify syndicate ringleaders and brokers.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

# Ensure backend root is in sys.path so app.* imports work smoothly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.nlp.entity_extractor import EntityExtractor
from app.nlp.relation_extractor import RelationExtractor


# Sample case dossier for demonstration
SAMPLE_CRIME_DOSSIER = """
INTELLIGENCE DOSSIER: OPERATION CYBER-STORM
Case Number: CASE-2024-8891 linked to FIR-112/2024.
Charges Filed: Booked under IPC 420, Section 120B IPC, and IT Act Section 66D.

Surveillance & Intercept Log:
Vikram Malhotra was identified as an accomplice of Rajesh Verma in coordinating illicit transfers.
Rajesh Verma conspired with Kabir Khan to acquire logistics clearance for contraband shipments.
Kabir Khan works for Apex Logistics Pvt Ltd and transferred funds to Titan Holdings.
Vikram Malhotra contacted Meera Rao regarding offshore communication channels.
Meera Rao was identified as an accomplice of Dinesh Karthik.
Dinesh Karthik contacted Apex Logistics Pvt Ltd.
Suspect vehicle DL 01 AB 1234 was tracked departing warehouse alongside truck MH-12-CD-5678.
Primary intercepted telephone line: +91 98765 43210.
"""



def build_criminal_network(text: str):
    """Extracts entities and relationships from text, returning graph data."""
    entity_extractor = EntityExtractor()
    extraction_result = entity_extractor.extract(text)

    relation_extractor = RelationExtractor()
    relation_result = relation_extractor.extract(text, extraction_result)

    # Build adjacency list: node -> set of connected nodes
    network = defaultdict(set)
    edge_types = []

    for rel in relation_result.relations:
        src = rel.source_entity.value
        tgt = rel.target_entity.value
        rel_type = rel.relation_type

        network[src].add(tgt)
        network[tgt].add(src)
        edge_types.append((src, rel_type, tgt))

    return extraction_result.entities, edge_types, network


def calculate_centrality(network: dict[str, set[str]]) -> list[tuple[str, int]]:
    """Calculates Degree Centrality (total connections) for each entity."""
    degrees = [(node, len(neighbors)) for node, neighbors in network.items()]
    # Sort highest degree first
    degrees.sort(key=lambda x: x[1], reverse=True)
    return degrees


def print_intelligence_report(entities, edge_types, degrees):
    """Prints a structured ASCII intelligence report."""
    print("=" * 70)
    print(" 🕵️  TRINETRA INTELLIGENCE NETWORK REPORT")
    print("=" * 70)

    # 1. Entities
    print(f"\n[+] DISCOVERED ENTITIES ({len(entities)} Total):")
    entity_by_type = defaultdict(list)
    for e in entities:
        entity_by_type[e.entity_type].append(e.value)

    for etype, values in entity_by_type.items():
        unique_vals = sorted(set(values))
        print(f"  • {etype} ({len(unique_vals)}): {', '.join(unique_vals)}")

    # 2. Relations
    print(f"\n[+] EXTRACTED RELATIONSHIPS ({len(edge_types)} Total):")
    for src, rel, tgt in edge_types:
        icon = "🚨" if rel == "ACCOMPLICE_OF" else "🔗"
        print(f"  {icon} [{src}] --({rel})--> [{tgt}]")

    # 3. Network Analysis / Centrality
    print("\n[+] SUSPECT CENTRALITY RANKINGS (Potential Syndicate Hubs / Ringleaders):")
    print("  Rank | Entity Name                 | Direct Ties (Degree)")
    print("  " + "-" * 55)
    for rank, (name, degree) in enumerate(degrees, start=1):
        status = "⚠️  HIGH-DEGREE NODE" if degree >= 2 else "   Periphery"
        print(f"  {rank:<4} | {name:<27} | {degree:<3} {status}")

        if degrees:
            top_suspect, max_deg = degrees[0]
            print(f"\n🚨 KEY FINDING: Most connected node is '{top_suspect}' with {max_deg} direct links.")

    # 4. Forensic & Legal Highlights
    penal_sections = set(entity_by_type.get("PENAL_SECTION", []))
    vehicles = set(entity_by_type.get("VEHICLE", []))
    if penal_sections or vehicles:
        print("\n[+] FORENSIC & LEGAL CHARGES OVERVIEW:")
        if penal_sections:
            print(f"  ⚖️  Penal Sections Invoked: {', '.join(sorted(penal_sections))}")
        if vehicles:
            print(f"  🚗  Vehicles Identified:    {', '.join(sorted(vehicles))}")

    print("=" * 70 + "\n")



def main():
    print("\nProcessing Crime Dossier through TRINETRA Intelligence Pipeline...")
    entities, edge_types, network = build_criminal_network(SAMPLE_CRIME_DOSSIER)
    degrees = calculate_centrality(network)
    print_intelligence_report(entities, edge_types, degrees)


if __name__ == "__main__":
    main()

