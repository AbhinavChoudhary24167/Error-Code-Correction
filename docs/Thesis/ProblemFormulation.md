# Problem Formulation

The thesis investigates sustainability-aware ECC strategies for standalone SRAMs. The section will evolve, but the initial outline captures the core objectives and assumptions.

## Goals
- Define how reliability, energy, and area trade-offs guide ECC selection.
- Explore SEC-DED and BCH codes for diverse fault models.
- Establish metrics for sustainability alongside traditional correctness measures.

## Assumptions
- Faults manifest as single, random, or burst bit flips within SRAM words.
- Simulators operate on sparse memory models to scale to GB ranges.
- Energy estimates rely on simplified gate-count models.

## Simulator Roles
- **Hamming32bit1Gb** – baseline SEC-DED evaluation for smaller word widths.
- **Hamming64bit128Gb** – tests large capacity memory with SEC-DED.
- **BCHvsHamming** – compares multi-bit resilience of BCH and Hamming schemes.

These points provide a structure for elaborating the research problem in later drafts.
