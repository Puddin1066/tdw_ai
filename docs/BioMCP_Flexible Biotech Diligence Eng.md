# TDW_AI: Flexible Biotech Diligence Engine

## Executive Summary

TDW_AI is a configurable biotech diligence platform that transforms incomplete scientific, clinical, and commercial inputs into reproducible, citation-backed diligence packets.

Unlike traditional chatbots, TDW_AI generates:

- Structured quantitative metrics
- Qualitative evidence summaries
- Source citations
- Comparative scorecards
- Cached diligence records
- Longitudinal opportunity tracking

The system accepts whatever information a user possesses and dynamically adjusts its evidence-gathering strategy.

Examples:

### Minimal Input

Target: STING

### Intermediate Input

Target: STING
Indication: Pancreatic Cancer

### Rich Input

Target: TMEM173 (STING)
Indication: Metastatic Pancreatic Ductal Adenocarcinoma
Mechanism Direction: Activate
Modality: Small Molecule Agonist
Patient Segment: KRAS Mutant
Geography: US/EU
Development Stage: Preclinical

The system automatically selects the appropriate evidence modules and generates a comprehensive diligence report.

---

# Product Vision

Create a reusable diligence engine capable of evaluating:

- Therapeutic targets
- Drug candidates
- Biotechnology companies
- Research programs
- Disease opportunities
- Licensing opportunities
- Venture investments
- Academic technologies

The objective is not to provide a single answer.

The objective is to produce a structured evidence package supporting decision making.

---

# Core Product Principles

## Flexible Inputs

Users should never be forced into a rigid workflow.

The system must gracefully handle:

- One field
- Several fields
- Complete datasets

The diligence workflow should adapt dynamically.

---

## Reproducibility

Every diligence run must be reproducible.

All source data must be stored.

All generated outputs must be timestamped.

All scores must be explainable.

---

## Auditability

Every claim must be linked to evidence.

Every score must be traceable.

Every source payload should be archived.

---

## Comparison Capability

Diligence outputs become structured records.

Users can compare:

- Targets
- Indications
- Companies
- Programs
- Historical runs

over time.

---

# User Workflow

## Step 1

Open New Diligence Run

---

## Step 2

Populate any available fields

Examples:

### Target Only

STING

### Target + Indication

STING
Pancreatic Cancer

### Asset Evaluation

Drug Candidate
Company
Indication
Clinical Stage

---

## Step 3

System normalizes entities

Examples:

TMEM173 → STING

PDAC → Pancreatic Ductal Adenocarcinoma

---

## Step 4

Evidence modules selected automatically

---

## Step 5

Data retrieved

Sources include:

- BioMCP
- PubMed
- ClinicalTrials.gov
- Open Targets
- OpenFDA
- UniProt
- Reactome
- NIH RePORTER

---

## Step 6

Scores calculated

---

## Step 7

Narrative memo generated

---

## Step 8

Results cached

---

## Step 9

Opportunity becomes searchable and comparable

---

# Input Schema

## Biology

- Target
- Target Alias
- Mechanism Direction
- Modality

## Disease

- Indication
- Patient Segment
- Geography

## Program

- Asset
- Company
- Development Stage
- Comparators

## Commercial

- Strategic Question
- Licensing Question
- Investment Question

---

# Evidence Module Architecture

Each module returns:

1. Quantitative Outputs
2. Qualitative Outputs
3. Citations
4. Raw Evidence References

---

# Evidence Modules

## Entity Resolution

### Quantitative

- Match Confidence
- Synonym Count

### Qualitative

- Normalization Notes

---

## Input Completeness

### Quantitative

- Percentage Complete

### Qualitative

- Missing Information Summary

---

## Target Biology

### Quantitative

- Pathway Count
- Protein Annotation Count

### Qualitative

- Biological Function Summary

---

## Disease Landscape

### Quantitative

- Trial Count
- Publication Count
- Grant Count

### Qualitative

- Disease Overview
- Unmet Need Discussion

---

## Target-Disease Association

### Quantitative

- Evidence Count
- Association Score

### Qualitative

- Biological Plausibility Assessment

---

## Human Genetics

### Quantitative

- Variant Count
- GWAS Evidence Count
- ClinVar Evidence Count

### Qualitative

- Human Validation Narrative

---

## Mechanism Direction Support

### Quantitative

- Activation Support Score
- Inhibition Support Score

### Qualitative

- Directionality Justification

---

## Pathway Plausibility

### Quantitative

- Pathway Overlap Score
- Network Connectivity Score

### Qualitative

- Mechanistic Interpretation

---

## Expression Relevance

### Quantitative

- Tissue Match Score
- Disease Expression Score

### Qualitative

- Expression Analysis

---

## Clinical Validation

### Quantitative

- Active Trials
- Completed Trials
- Trial Phase Distribution

### Qualitative

- Clinical Maturity Assessment

---

## Competitive Landscape

### Quantitative

- Competitor Count
- Maximum Phase
- Sponsor Concentration

### Qualitative

- Competitive Analysis

---

## Failure History

### Quantitative

- Failed Trial Count
- Terminated Program Count

### Qualitative

- Failure Mode Discussion

---

## Safety Liability

### Quantitative

- Safety Risk Score
- Adverse Event Signal Count

### Qualitative

- Safety Narrative

---

## Druggability

### Quantitative

- Modality Fit Score
- Precedent Count

### Qualitative

- Development Feasibility Assessment

---

## Biomarkerability

### Quantitative

- Biomarker Count
- Companion Diagnostic Count

### Qualitative

- Patient Selection Strategy

---

## Regulatory Precedent

### Quantitative

- Approved Analog Count
- Regulatory Pathway Similarity Score

### Qualitative

- Regulatory Interpretation

---

## Commercial Attractiveness

### Quantitative

- Market Size Proxy
- Pricing Proxy
- Competitive Density

### Qualitative

- Commercial Opportunity Assessment

---

## IP Landscape

### Quantitative

- Patent Family Count
- Assignee Concentration

### Qualitative

- White Space Analysis

---

## Funding Momentum

### Quantitative

- Grants Per Year
- Funding Growth Rate

### Qualitative

- Funding Environment Assessment

---

## Publication Momentum

### Quantitative

- Publications Per Year
- Citation Velocity

### Qualitative

- Research Momentum Assessment

---

## Data Quality

### Quantitative

- Citation Count
- Source Diversity Score
- Recency Score

### Qualitative

- Confidence Assessment

---

## Final Thesis

### Quantitative

Overall Opportunity Score

### Qualitative

Advance

Watch

Deprioritize

Recommendation

---

# Quantitative Scoring System

All modules scored independently.

Scale:

0 = None
1 = Weak
2 = Limited
3 = Moderate
4 = Strong
5 = Exceptional

Risk Scores:

0 = Minimal Risk
5 = Severe Risk

---

# Core Dashboard Components

## Snapshot Card

High-level opportunity summary

---

## Quantitative Scorecard

All module scores

---

## Radar Chart

Opportunity profile

Dimensions:

- Genetics
- Clinical
- Safety
- Druggability
- Biomarkers
- Commercial
- Competition
- Evidence

---

## Trial Landscape Chart

Trial count by phase

---

## Publication Timeline

Publications over time

---

## Grant Timeline

Funding activity over time

---

## Competitor Table

Company
Asset
Mechanism
Phase

---

## Citation Browser

Every supporting source

---

## Missing Evidence Panel

Outstanding diligence questions

---

# Data Storage

Each run becomes a permanent diligence record.

Store:

- Inputs
- Outputs
- Scores
- Citations
- Source payloads
- Generated narratives
- Metadata

---

# Run Schema

Each run contains:

- Unique Identifier
- Timestamp
- Inputs
- Normalized Entities
- Module Outputs
- Quantitative Scores
- Qualitative Summary
- Citations
- Raw Source References

---

# Sources

## Primary Sources

- BioMCP
- PubMed
- ClinicalTrials.gov
- Open Targets
- OpenFDA
- UniProt
- Reactome
- NIH RePORTER
- MyGene
- MyVariant
- MyChem

---

# Backend Architecture

## Frontend

Next.js

shadcn/ui

TypeScript

---

## Database

PostgreSQL

Supabase

Prisma

---

## Retrieval

BioMCP

Direct API integrations

---

## AI Layer

OpenAI API

Structured prompt templates

Evidence-grounded generation only

---

# Development Roadmap

## Phase 1

Static prototype

- Input forms
- Mock outputs
- Charts
- Results page

---

## Phase 2

Persistence

- Database
- Run history
- Comparison views

---

## Phase 3

Module Router

Dynamic module selection

---

## Phase 4

BioMCP Integration

Live evidence retrieval

---

## Phase 5

Direct API Integrations

- Open Targets
- ClinicalTrials.gov
- PubMed
- OpenFDA
- UniProt

---

## Phase 6

Memo Generation

Automated diligence reports

---

## Phase 7

Portfolio Analytics

Cross-run comparison

Trend analysis

Ranking systems

---

# Long-Term Vision

TDW_AI becomes a continuously expanding diligence database.

Each run contributes:

- Structured evidence
- Quantitative metrics
- Qualitative interpretations
- Historical comparisons

The resulting dataset evolves into a proprietary biotechnology opportunity intelligence platform capable of comparing targets, indications, programs, companies, and investment opportunities using reproducible evidence-based analysis.