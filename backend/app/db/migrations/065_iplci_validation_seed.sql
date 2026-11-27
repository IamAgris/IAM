-- IPLCI validation checklist — the exact questions qualified counsel must close.
-- Seeded pending: the system never marks them verified on its own.

WITH seed(domain, subject, jurisdiction, question, official_source_url) AS (
    VALUES
        ('privacy', 'POPIA research processing', 'ZA',
         'Confirm the current text, conditions and safeguards for research processing (section 27) and whether they apply to IAM corpora.',
         'https://www.gov.za/documents/protection-personal-information-act'),
        ('copyright', 'South Africa Copyright Act exceptions', 'ZA',
         'Confirm the operative copyright exceptions after the 2026 Constitutional Court judgment and the commencement status of any amendment.',
         'https://www.gov.za'),
        ('trademark', 'South Africa Trade Marks Act', 'ZA',
         'Confirm registration, classes and territory requirements for marks IAM proposes to adopt.',
         'https://www.cipc.co.za'),
        ('patent', 'South Africa Patents Act', 'ZA',
         'Confirm patent term, enforceability and freedom-to-operate requirements before implementation.',
         'https://www.cipc.co.za'),
        ('consumer', 'Consumer Protection Act', 'ZA',
         'Confirm consumer representation, refund and advertising obligations for commercial activity.',
         'https://www.gov.za'),
        ('privacy', 'GDPR lawful basis and AI training', 'EU',
         'Confirm lawful bases, TDM exceptions and safeguards for research and model training.',
         'https://eur-lex.europa.eu'),
        ('ai', 'EU AI Act obligations', 'EU',
         'Confirm which AI Act obligations apply to IAM research, deployment and commercial operation.',
         'https://eur-lex.europa.eu'),
        ('copyright', 'Directive 2019/790 Article 4', 'EU',
         'Confirm territorial applicability, reservation of rights and commercial TDM conditions.',
         'https://eur-lex.europa.eu'),
        ('platform', 'Digital Services Act', 'EU',
         'Confirm platform and hosted-content obligations for any IAM-operated service.',
         'https://eur-lex.europa.eu'),
        ('privacy', 'UK GDPR and Data Protection Act 2018', 'UK',
         'Confirm lawful bases, research safeguards and transfer rules under UK law.',
         'https://www.legislation.gov.uk'),
        ('copyright', 'UK CDPA exceptions', 'UK',
         'Confirm current copyright exceptions and text-and-data-mining provisions.',
         'https://www.legislation.gov.uk'),
        ('copyright', 'US Copyright Act and DMCA', 'US',
         'Confirm reproduction, fair use, notice-and-takedown and anti-circumvention boundaries.',
         'https://www.copyright.gov'),
        ('trademark', 'Lanham Act', 'US',
         'Confirm infringement, dilution and nominative-use boundaries for proposed names.',
         'https://www.uspto.gov'),
        ('patent', 'US Patent Act', 'US',
         'Confirm enforceability, claim scope and freedom-to-operate requirements.',
         'https://www.uspto.gov'),
        ('privacy', 'US state privacy laws', 'US',
         'Confirm which state privacy regimes apply to data IAM collects and processes.',
         'https://www.ncsl.org'),
        ('privacy', 'International transfers and residency', 'GLOBAL',
         'Confirm lawful transfer mechanisms for every origin/destination pair IAM uses.',
         'https://www.wipo.int')
)
INSERT INTO ip_legal_validation_tasks (
    id, domain, subject, jurisdiction, question, official_source_url,
    status, payload, created_at
)
SELECT
    gen_random_uuid(), s.domain, s.subject, s.jurisdiction, s.question, s.official_source_url,
    'pending', '{"source":"OD-48 validation seed"}'::jsonb, NOW()
FROM seed s
WHERE NOT EXISTS (
    SELECT 1 FROM ip_legal_validation_tasks t
    WHERE t.subject = s.subject
      AND t.jurisdiction IS NOT DISTINCT FROM s.jurisdiction
);
