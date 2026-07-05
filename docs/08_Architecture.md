RetailPilot AI
System Architecture and Technical Design

Document Version: 1.0
Project Version: v1.0.0-alpha
Status: Architecture Definition
Author: Badal Kushwaha
Product: AI-Powered Retail Business Intelligence Platform

1. Purpose

This document defines the technical architecture of RetailPilot AI.

The architecture is designed to support rapid MVP development while maintaining modularity, testability, and a clear path for future expansion.

The MVP will use a modular monolith architecture rather than independent microservices.

This approach provides:

Faster development
Simpler deployment
Easier debugging
Lower infrastructure complexity
Clear separation of responsibilities
Future migration path to service-based architecture
2. Architecture Goals

The technical architecture should support:

CSV dataset upload
Data validation
Data cleaning
Business analytics
Interactive dashboards
Machine Learning workflows
Sales forecasting
Customer segmentation
Recommendation generation
Business Health Score calculation
Report generation
Demo Mode

The architecture should remain understandable enough for internship presentation and technical interviews.

3. Architecture Style

RetailPilot AI MVP will follow a:

Modular Monolith Architecture

This means the application will be deployed as one system while maintaining clear internal modules.

High-level flow:

User Interface

↓

Application Orchestration

↓

Data Validation and Processing

↓

Analytics and Feature Engineering

↓

Machine Learning and Forecasting

↓

Business Intelligence Logic

↓

Visualization and Reports

The modules will communicate through clearly defined Python functions, classes, configuration objects, and shared data structures.

4. Proposed Technology Stack
Programming Language

Python

Primary use:

Data processing
Analytics
Machine Learning
Forecasting
Application logic
Report generation
MVP Application Framework

Streamlit

Purpose:

Interactive web application
Dashboard development
File upload
Charts and KPIs
User interaction
Rapid MVP deployment

Streamlit is selected for the internship MVP because it allows the project to focus development effort on Data Science and business intelligence functionality.

Data Processing

Primary libraries:

Pandas
NumPy

Responsibilities:

Data loading
Validation support
Cleaning
Transformation
Aggregation
Feature engineering
Data Visualization

Primary options:

Plotly
Streamlit native visualization components

Responsibilities:

Interactive charts
Trend visualization
Forecast plots
Product analysis
Customer analysis
Machine Learning

Primary library:

Scikit-learn

Possible use cases:

Data preprocessing
Feature scaling
K-Means clustering
Evaluation metrics
Supporting ML utilities
Forecasting

Candidate libraries and approaches:

Statsmodels
Prophet, if justified by testing
Scikit-learn-compatible regression approaches
XGBoost, if selected after evaluation

The final forecasting model will be chosen based on validation performance and implementation feasibility.

Report Generation

Possible MVP approach:

ReportLab for PDF generation

The report module should convert calculated analytical outputs into a structured business report.

Model Persistence

Possible tools:

Joblib
Trusted local serialization where required

Saved model artifacts should be stored separately from source code.

5. Logical Architecture

The system is divided into the following logical layers:

Layer 1 — Presentation Layer

Responsibilities:

Navigation
User inputs
File upload
KPI display
Chart rendering
Filter controls
Error messages
Download actions

The presentation layer should not contain complex analytical logic.

Layer 2 — Application Layer

Responsibilities:

Coordinate user workflow
Manage analysis session state
Trigger validation
Trigger cleaning
Trigger analytics
Trigger ML modules
Prepare results for UI
Coordinate report generation

This layer connects the interface with analytical services.

Layer 3 — Data Processing Layer

Responsibilities:

Read uploaded files
Validate schema
Parse dates
Convert data types
Handle duplicates
Assess missing values
Standardize categories
Create derived financial metrics
Generate cleaning summaries
Layer 4 — Analytics Layer

Responsibilities:

KPI calculations
Time-based analysis
Geographic analysis
Category analysis
Brand analysis
Product analysis
Customer summary analysis
Comparative analysis

This layer should provide reusable analytical functions.

Layer 5 — Machine Learning Layer

Responsibilities:

Customer feature preparation
RFM calculation
Feature scaling
Clustering
Cluster evaluation
Forecast preparation
Forecast training
Forecast evaluation
Prediction generation
Layer 6 — Business Intelligence Layer

Responsibilities:

Business Health Score
Product classification logic
Demand-based inventory recommendations
Risk identification
Opportunity identification
Recommendation generation
Insight prioritization

This layer converts analytical outputs into decision-support information.

Layer 7 — Reporting Layer

Responsibilities:

Report content preparation
KPI summaries
Chart exports where needed
Forecast summary
Customer segment summary
Recommendations
PDF generation
CSV export
6. Recommended Project Structure

The project structure should evolve toward:

RetailPilot-AI/
│
├── app/
│   ├── main.py
│   ├── pages/
│   └── components/
│
├── backend/
│   ├── data_loader.py
│   ├── validator.py
│   ├── cleaner.py
│   ├── analytics.py
│   ├── health_score.py
│   ├── recommendations.py
│   └── report_service.py
│
├── ml/
│   ├── customer_segmentation.py
│   ├── forecasting.py
│   ├── feature_engineering.py
│   └── evaluation.py
│
├── models/
│
├── data/
│   ├── demo/
│   └── processed/
│
├── docs/
│
├── assets/
│
├── prompts/
│
├── reports/
│
├── screenshots/
│
├── tests/
│   ├── test_validator.py
│   ├── test_cleaner.py
│   ├── test_analytics.py
│   └── test_health_score.py
│
├── .gitignore
├── CHANGELOG.md
├── LICENSE
├── README.md
└── requirements.txt

The final implementation may adjust individual filenames as development requirements become clearer.

7. Application Data Flow

The primary application flow is:

CSV Upload or Demo Dataset

↓

File Reader

↓

Schema Validator

↓

Data Quality Assessment

↓

Cleaning Pipeline

↓

Derived Metric Calculation

↓

Session Data Store

↓

Analytics Engine

↓

ML Modules

↓

Business Intelligence Layer

↓

Dashboard and Reports

The cleaned dataset should become the shared analytical source for downstream modules.

8. Dataset State Strategy

For the MVP, the application may use session-based state management.

Possible states include:

Raw Dataset
Validation Result
Cleaned Dataset
KPI Results
Analytics Results
Customer Segments
Forecast Results
Business Health Score
Recommendations

The MVP should avoid unnecessary permanent storage of uploaded user datasets.

Future SaaS versions may introduce persistent database and object storage.

9. Demo Mode Architecture

Demo Mode should use the same analytical pipeline as user-uploaded datasets whenever practical.

Flow:

Demo Button

↓

Load Demo Dataset

↓

Validation

↓

Cleaning or Prevalidated Processing

↓

Analytics

↓

ML Modules

↓

Dashboard

Using the same pipeline reduces duplicated logic and demonstrates that the product is functioning on actual structured data.

10. Data Validation Architecture

The validator should produce a structured validation result.

Possible output:

Validation Status
Missing Required Columns
Optional Missing Columns
Data Type Problems
Invalid Date Count
Missing Value Summary
Duplicate Count
Business Rule Warnings

The UI should display these results in understandable language.

Validation logic should remain separate from UI rendering.

11. Analytics Architecture

Analytics functions should receive cleaned data and return structured results.

Example conceptual pattern:

Input:

Cleaned DataFrame

Output:

KPI Dictionary
Trend DataFrames
Product Summary
Category Summary
City Summary
Brand Summary

The UI layer will decide how these outputs are visualized.

This separation prevents analytical logic from becoming tightly coupled to dashboard code.

12. ML Architecture

Each ML module should contain task-specific steps.

Customer Segmentation

Input:

Cleaned transaction dataset

Process:

Customer aggregation
RFM features
Transformation
Scaling
Clustering
Evaluation
Cluster profiling

Output:

Customer segments
Cluster metrics
Segment profiles
Business labels
Forecasting

Input:

Cleaned transaction dataset

Process:

Time aggregation
Missing period handling
Train-validation split
Baseline forecasting
Candidate model training
Evaluation
Model selection
Future prediction

Output:

Historical series
Forecast series
Evaluation metrics
Model metadata
Warnings
13. Business Intelligence Architecture

The Business Intelligence Layer should consume analytical outputs rather than recalculate raw data unnecessarily.

Possible inputs:

KPI changes
Trend results
Product rankings
Customer segments
Forecast direction
Margin analysis
Inventory signals

Outputs:

Health Score
Risk Flags
Opportunity Flags
Prioritized Recommendations
Evidence Statements

This design helps keep recommendations connected to measurable results.

14. Business Health Score Architecture

The Business Health Score should use component-based calculation.

Conceptual flow:

Metric Calculation

↓

Metric Normalization

↓

Component Score Calculation

↓

Missing Component Handling

↓

Weighted Aggregation

↓

Overall Score

↓

Score Band

↓

Explanation

The system should return both the overall score and component-level details.

15. Recommendation Engine Architecture

The MVP recommendation engine will use a transparent hybrid design.

Pipeline:

Analytics Result

↓

Condition Evaluation

↓

Evidence Extraction

↓

Recommendation Rule

↓

Priority Score

↓

Business-Friendly Output

Possible priority levels:

Critical
High
Medium
Informational

Recommendations should include:

Finding
Evidence
Suggested Action
Priority

Future versions may add generative AI for language refinement or conversational interaction, but core recommendations should remain grounded in analytical evidence.

16. Error Handling Strategy

The application should fail gracefully.

Examples:

Invalid CSV

Display validation errors without crashing.

Missing CustomerID

Disable customer segmentation and explain why.

Insufficient Time History

Disable or limit forecasting.

Missing Cost Data

Hide profit-related KPIs or clearly mark them unavailable.

Missing Stock Data

Provide demand analysis instead of exact inventory recommendations.

Model Failure

Show descriptive analytics and a clear warning.

One failed module should not unnecessarily break the entire application.

17. Configuration Strategy

Important settings should be centralized where practical.

Possible configuration values:

Required columns
Optional columns
Column aliases
Supported date formats
Forecast horizon
Minimum history requirement
Clustering configuration
Health Score weights
Recommendation thresholds
Upload limits

Configuration should not be unnecessarily duplicated across modules.

18. Testing Architecture

Testing should focus on high-value logic.

Data Validation Tests

Test:

Missing required columns
Invalid numeric fields
Invalid dates
Empty dataset
Duplicate rows
Cleaning Tests

Test:

Duplicate removal
Date parsing
Derived calculations
Category standardization
Analytics Tests

Test:

Revenue calculation
Profit calculation
KPI aggregation
Product ranking
ML Tests

Test:

Feature preparation
Output shape
Missing field handling
Insufficient data handling
Business Logic Tests

Test:

Health Score boundaries
Missing component handling
Recommendation triggers
19. Security and Privacy Considerations

For the MVP:

Do not require customer names.
Use anonymous CustomerID values.
Avoid logging sensitive uploaded data.
Keep uploaded data session-scoped where possible.
Do not commit datasets containing personal information.
Do not commit credentials or API keys.
Use environment variables for future secrets.

Future production versions will require stronger controls for:

Authentication
Authorization
Encryption
Data retention
Secure storage
Audit logging
20. Deployment Strategy

The MVP deployment target should support:

Python
Streamlit
Required ML libraries
PDF generation dependencies
Public demonstration

The deployment workflow should include:

Local Development

↓

Git Commit

↓

Push to GitHub

↓

Deployment Build

↓

Dependency Installation

↓

Application Start

↓

Smoke Testing

The exact hosting provider will be selected during the deployment phase based on compatibility, resource limits, and project needs.

21. Future Architecture Evolution

The architecture may evolve in stages.

MVP

Modular Streamlit application.

Version 2

Streamlit or modern frontend with API-based backend and persistent database.

Possible separation:

Frontend

↓

REST API

↓

Analytics Services

↓

ML Services

↓

Database and Object Storage

Version 3 and Beyond

Selected high-load modules may become independent services only when scale and operational requirements justify the complexity.

Microservices should not be introduced solely for appearance.

22. Architecture Decision Summary

The MVP architecture decisions are:

Python-first development
Streamlit for rapid interactive application development
Modular monolith instead of premature microservices
Pandas and NumPy for data processing
Plotly for interactive analytics
Scikit-learn for core ML workflows
Time-aware forecasting evaluation
Session-based MVP data handling
Evidence-based recommendation engine
Explainable Business Health Score
Report generation as an independent module
Clear separation between UI and analytical logic
Future-ready path toward API-based architecture
23. Architecture Success Criteria

The architecture will be considered successful when:

Core modules can be developed independently.
UI code does not contain major analytical logic.
Dataset validation is reusable.
Analytics functions are testable.
ML outputs are structured and explainable.
Missing data disables unsupported modules gracefully.
Demo Mode and uploaded data use consistent processing logic.
Reports use the same analytical results as the dashboard.
The MVP can be deployed as one manageable application.
Future migration does not require rebuilding all business logic.
Conclusion

RetailPilot AI will use a practical modular architecture designed for both rapid MVP development and future growth.

The internship version will remain simple enough to build, test, deploy, and explain within the available timeline while maintaining clear boundaries between presentation, data processing, analytics, Machine Learning, business intelligence, and reporting.

The architecture prioritizes business value and maintainability over unnecessary technical complexity.