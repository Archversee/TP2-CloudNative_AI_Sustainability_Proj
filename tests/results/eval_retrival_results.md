================================================================================
ECOEYE RETRIEVAL QUALITY EVALUATION
================================================================================

Testing 5 queries...
API Endpoint: http://localhost:30800

================================================================================
EVALUATING AT DEFAULT THRESHOLD (0.4)
================================================================================

============================================================
Query: What are Fairprice's Scope 1 emissions?
Category: numeric
Filter: Fairprice (2024)
============================================================

Retrieved pages: [16, 16, 16, 15]
Expected pages: [16, 40]

Metrics:
  Precision@5: 75.00%
  Recall@5:    150.00%
  MRR:         1.000

============================================================
Query: What are PUB's Scope 2 emissions?
Category: numeric
Filter: Pub (2025)
============================================================

Retrieved pages: [49, 49, 48, 48]
Expected pages: [48, 49]

Metrics:
  Precision@5: 100.00%
  Recall@5:    200.00%
  MRR:         1.000

============================================================
Query: When does Fairprice target net zero?
Category: target
Filter: Fairprice (2024)
============================================================

Retrieved pages: [6]
Expected pages: [4, 6, 12]

Metrics:
  Precision@5: 100.00%
  Recall@5:    33.33%
  MRR:         1.000

============================================================
Query: What is SGX's net zero target year?
Category: target
Filter: Sgx (2025)
============================================================

Retrieved pages: [21, 4]
Expected pages: [21, 23]

Metrics:
  Precision@5: 50.00%
  Recall@5:    50.00%
  MRR:         1.000

============================================================
Query: Compare renewable energy usage
Category: comparative
============================================================

Retrieved pages: [17, 16, 48]
Expected pages: None

Companies in results: {'Pub', 'Fairprice'}

================================================================================
OVERALL METRICS (Threshold = 0.4)
================================================================================

Precision@5: 81.25%
Recall@5:    108.33%
MRR:         1.000
Avg Results: 2.8

================================================================================
CATEGORY ANALYSIS
================================================================================

Category        Count    Precision@5    Recall@5     MRR
----------------------------------------------------------------------
numeric         2        87.50%         175.00%      1.000
target          2        75.00%         41.67%       1.000
----------------------------------------------------------------------

================================================================================
THRESHOLD SENSITIVITY ANALYSIS
================================================================================

Threshold    Precision@5    Recall@5     MRR      Avg Results
----------------------------------------------------------------------

============================================================
Query: What are Fairprice's Scope 1 emissions?
Category: numeric
Filter: Fairprice (2024)
============================================================

Retrieved pages: [16, 16, 16, 15]
Expected pages: [16, 40]

Metrics:
  Precision@5: 75.00%
  Recall@5:    150.00%
  MRR:         1.000

============================================================
Query: What are PUB's Scope 2 emissions?
Category: numeric
Filter: Pub (2025)
============================================================

Retrieved pages: [49, 48]
Expected pages: [48, 49]

Metrics:
  Precision@5: 100.00%
  Recall@5:    100.00%
  MRR:         1.000

============================================================
Query: When does Fairprice target net zero?
Category: target
Filter: Fairprice (2024)
============================================================

Retrieved pages: [6]
Expected pages: [4, 6, 12]

Metrics:
  Precision@5: 100.00%
  Recall@5:    33.33%
  MRR:         1.000

============================================================
Query: What is SGX's net zero target year?
Category: target
Filter: Sgx (2025)
============================================================

Retrieved pages: [21, 4]
Expected pages: [21, 23]

Metrics:
  Precision@5: 50.00%
  Recall@5:    50.00%
  MRR:         1.000
0.3          81.25%         83.33%       1.000    2.2

============================================================
Query: What are Fairprice's Scope 1 emissions?
Category: numeric
Filter: Fairprice (2024)
============================================================

Retrieved pages: [16, 16, 16, 15]
Expected pages: [16, 40]

Metrics:
  Precision@5: 75.00%
  Recall@5:    150.00%
  MRR:         1.000

============================================================
Query: What are PUB's Scope 2 emissions?
Category: numeric
Filter: Pub (2025)
============================================================

Retrieved pages: [49, 48]
Expected pages: [48, 49]

Metrics:
  Precision@5: 100.00%
  Recall@5:    100.00%
  MRR:         1.000

============================================================
Query: When does Fairprice target net zero?
Category: target
Filter: Fairprice (2024)
============================================================

Retrieved pages: [6]
Expected pages: [4, 6, 12]

Metrics:
  Precision@5: 100.00%
  Recall@5:    33.33%
  MRR:         1.000

============================================================
Query: What is SGX's net zero target year?
Category: target
Filter: Sgx (2025)
============================================================

Retrieved pages: [21, 4]
Expected pages: [21, 23]
Expected pages: [21, 23]

Metrics:
  Precision@5: 50.00%
  Recall@5:    50.00%
  MRR:         1.000
0.4          81.25%         83.33%       1.000    2.2

============================================================
Query: What are Fairprice's Scope 1 emissions?
Category: numeric
Filter: Fairprice (2024)
============================================================






Expected pages: [21, 23]

Metrics:
  Precision@5: 50.00%
  Recall@5:    50.00%
  MRR:         1.000
0.4          81.25%         83.33%       1.000    2.2

============================================================
Query: What are Fairprice's Scope 1 emissions?
Category: numeric
Filter: Fairprice (2024)
============================================================

Expected pages: [21, 23]

Metrics:
  Precision@5: 50.00%
  Recall@5:    50.00%
  MRR:         1.000
0.4          81.25%         83.33%       1.000    2.2

============================================================
Query: What are Fairprice's Scope 1 emissions?
Expected pages: [21, 23]

Metrics:
Expected pages: [21, 23]


Metrics:
  Precision@5: 50.00%
  Recall@5:    50.00%
  MRR:         1.000
0.4          81.25%         83.33%       1.000    2.2

============================================================
Query: What are Fairprice's Scope 1 emissions?
Category: numeric
Filter: Fairprice (2024)
============================================================

Retrieved pages: [16, 16, 16, 15]
Expected pages: [16, 40]

Metrics:
  Precision@5: 75.00%
  Recall@5:    150.00%
  MRR:         1.000

============================================================
Query: What are PUB's Scope 2 emissions?
Category: numeric
Filter: Pub (2025)
============================================================

Retrieved pages: [49, 48]
Expected pages: [48, 49]

Metrics:
  Precision@5: 100.00%
  Recall@5:    100.00%
  MRR:         1.000

============================================================
Query: When does Fairprice target net zero?
Category: target
Filter: Fairprice (2024)
============================================================

Retrieved pages: [6]
Expected pages: [4, 6, 12]

Metrics:
  Precision@5: 100.00%
  Recall@5:    33.33%
  MRR:         1.000

============================================================
Query: What is SGX's net zero target year?
Category: target
Filter: Sgx (2025)
============================================================

Retrieved pages: [21, 4]
Expected pages: [21, 23]

Metrics:
  Precision@5: 50.00%
  Recall@5:    50.00%
  MRR:         1.000
0.5          81.25%         83.33%       1.000    2.2

============================================================
Query: What are Fairprice's Scope 1 emissions?
Category: numeric
Filter: Fairprice (2024)
============================================================

Retrieved pages: [16, 16, 16, 15]
Expected pages: [16, 40]

Metrics:
  Precision@5: 75.00%
  Recall@5:    150.00%
  MRR:         1.000

============================================================
Query: What are PUB's Scope 2 emissions?
Category: numeric
Filter: Pub (2025)
============================================================

Retrieved pages: [49]
Expected pages: [48, 49]

Metrics:
  Precision@5: 100.00%
  Recall@5:    50.00%
  MRR:         1.000

============================================================
Query: When does Fairprice target net zero?
Category: target
Filter: Fairprice (2024)
============================================================

Retrieved pages: [6]
Expected pages: [4, 6, 12]

Metrics:
  Precision@5: 100.00%
  Recall@5:    33.33%
  MRR:         1.000

============================================================
Query: What is SGX's net zero target year?
Category: target
Filter: Sgx (2025)
============================================================

Retrieved pages: [21, 4]
Expected pages: [21, 23]

Metrics:
  Precision@5: 50.00%
  Recall@5:    50.00%
  MRR:         1.000
0.6          81.25%         70.83%       1.000    2.0
----------------------------------------------------------------------

✓ Results saved to retrieval_quality_results.json

================================================================================
EVALUATION COMPLETE
================================================================================