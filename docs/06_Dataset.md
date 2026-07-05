# RetailPilot AI

# Dataset Specification and Data Strategy

**Document Version:** 1.0
**Project Version:** v1.0.0-alpha
**Status:** Planning
**Author:** Badal Kushwaha
**Product:** AI-Powered Retail Business Intelligence Platform

---

# 1. Purpose

This document defines the dataset structure, data requirements, validation rules, derived features, and data strategy for RetailPilot AI.

The objective is to ensure that all analytics, dashboards, machine learning models, forecasts, recommendations, and reports use a consistent and reliable data foundation.

The MVP will initially focus on electronics retail transaction data.

---

# 2. Dataset Strategy

RetailPilot AI will use two dataset approaches.

## 2.1 Demo Dataset

A realistic electronics retail dataset will be prepared for:

* Product demonstrations
* Development
* Testing
* Internship evaluation
* College presentation
* Recruiter demonstrations
* Demo Mode

The demo dataset should contain realistic patterns instead of completely random values.

Examples of realistic patterns:

* Seasonal demand changes
* Weekend sales differences
* Product-specific price ranges
* Different category profit margins
* City-level performance variation
* Repeat customer behavior
* Discount effects
* Fast-moving and slow-moving products

---

## 2.2 User-Uploaded Dataset

Users will be able to upload CSV files.

The MVP will support a documented schema and validate required columns.

Future versions may include:

* Column mapping interface
* Automatic column detection
* Schema inference
* Multiple file formats
* POS connectors
* Database integrations

---

# 3. Dataset Granularity

The primary dataset will use transaction-line-level granularity.

Each row represents one product line within an order.

Example:

One order containing a laptop, mouse, and keyboard may create three rows with the same OrderID but different ProductID values.

This structure supports:

* Order analysis
* Product analysis
* Basket analysis in future versions
* Customer analysis
* Revenue calculations
* Profit calculations

---

# 4. Core Dataset Schema

The recommended MVP dataset includes the following columns.

| Column         | Data Type | Requirement                     | Description                            |
| -------------- | --------- | ------------------------------- | -------------------------------------- |
| OrderID        | String    | Required                        | Unique order identifier                |
| OrderDate      | Date      | Required                        | Date of transaction                    |
| CustomerID     | String    | Required for customer analytics | Unique customer identifier             |
| ProductID      | String    | Required                        | Unique product identifier              |
| ProductName    | String    | Required                        | Product display name                   |
| Category       | String    | Required                        | Main product category                  |
| SubCategory    | String    | Optional                        | Detailed product classification        |
| Brand          | String    | Recommended                     | Product brand                          |
| City           | String    | Recommended                     | Sales location                         |
| Quantity       | Integer   | Required                        | Number of units sold                   |
| UnitPrice      | Float     | Required                        | Selling price per unit before discount |
| DiscountPct    | Float     | Recommended                     | Discount percentage                    |
| UnitCost       | Float     | Required for profit analytics   | Cost per unit                          |
| PaymentMethod  | String    | Optional                        | Payment method used                    |
| StockAvailable | Integer   | Optional                        | Available stock snapshot               |

---

# 5. Recommended Electronics Categories

The demo dataset may contain categories such as:

* Laptops
* Monitors
* Storage
* Computer Components
* Networking
* Peripherals
* Audio
* Gaming Accessories
* Mobile Accessories
* Power Accessories

---

# 6. Example Product Types

Possible products include:

## Laptops

* Gaming Laptop
* Business Laptop
* Student Laptop
* Ultrabook

## Peripherals

* Mouse
* Keyboard
* Webcam
* Printer
* Scanner

## Storage

* SSD
* HDD
* USB Drive
* Memory Card

## Computer Components

* RAM
* Graphics Card
* Processor
* Motherboard
* Power Supply

## Networking

* Wi-Fi Router
* Network Switch
* USB Wi-Fi Adapter

## Audio

* Headphones
* Speakers
* Gaming Headset

The final demo dataset should use realistic product-brand-category relationships.

---

# 7. Derived Business Fields

RetailPilot AI should calculate analytical fields instead of requiring users to provide every business metric.

## GrossAmount

GrossAmount = Quantity × UnitPrice

## DiscountAmount

DiscountAmount = GrossAmount × DiscountPct / 100

## Revenue

Revenue = GrossAmount − DiscountAmount

## TotalCost

TotalCost = Quantity × UnitCost

## Profit

Profit = Revenue − TotalCost

## ProfitMarginPct

ProfitMarginPct = Profit / Revenue × 100

The application must safely handle zero revenue when calculating profit margin.

---

# 8. Time-Based Derived Features

From `OrderDate`, the system may derive:

* Year
* Quarter
* Month
* MonthName
* Week
* Day
* DayOfWeek
* IsWeekend

These fields will support:

* Trend analysis
* Seasonal analysis
* Monthly comparison
* Weekly patterns
* Forecasting preparation

---

# 9. Required Fields by Module

Not every module requires every column.

## Core Dashboard

Required:

* OrderID
* OrderDate
* ProductID
* Quantity
* UnitPrice

Profit KPIs additionally require:

* UnitCost

---

## Product Analytics

Required:

* ProductID
* ProductName
* Category
* Quantity
* UnitPrice

Recommended:

* Brand
* UnitCost
* DiscountPct

---

## Customer Analytics

Required:

* CustomerID
* OrderID
* OrderDate

Recommended:

* Revenue or fields required to derive Revenue

Without CustomerID, customer segmentation should be disabled rather than generating artificial customer results.

---

## Geographic Analytics

Required:

* City or another supported location field

If geographic data is unavailable, this module should be hidden or marked unavailable.

---

## Sales Forecasting

Required:

* OrderDate
* Revenue or fields required to derive Revenue

The dataset must contain sufficient historical coverage.

A minimum threshold will be determined during model testing.

The platform should refuse or warn against forecasting when historical data is insufficient.

---

## Inventory Intelligence

Preferred fields:

* ProductID
* ProductName
* Quantity
* OrderDate
* StockAvailable

If `StockAvailable` is unavailable, the system may provide demand trend recommendations but should not claim exact stock availability or exact reorder quantity.

---

# 10. Data Validation Rules

Before analysis, the uploaded dataset should be validated.

## File-Level Validation

Check:

* File format
* File readability
* Empty file
* Row count
* Column count
* Duplicate column names
* File size limit

---

## Column-Level Validation

Check:

* Required columns
* Data types
* Date parsing
* Numerical conversion
* Missing percentage
* Unexpected categories
* Duplicate identifiers where uniqueness is expected

---

## Business Rule Validation

Examples:

* Quantity should normally be greater than zero.
* UnitPrice should not be negative.
* UnitCost should not be negative.
* DiscountPct should remain within the supported range.
* OrderDate should be valid.
* CustomerID should not be blank when customer analysis is requested.
* ProductID should not be blank.
* StockAvailable should not be negative.

Returns and cancellations, if supported in future versions, should use explicit transaction types rather than being silently treated as invalid sales.

---

# 11. Data Cleaning Strategy

The cleaning pipeline should be transparent and reproducible.

Possible steps:

1. Standardize column names.
2. Trim unnecessary whitespace.
3. Parse dates.
4. Convert numeric fields.
5. Remove exact duplicate rows.
6. Standardize category labels.
7. Standardize brand labels.
8. Analyze missing values.
9. Flag suspicious values.
10. Create derived business fields.
11. Generate cleaning summary.

The platform should not silently remove large amounts of data without informing the user.

---

# 12. Missing Value Strategy

Missing values should be handled according to business meaning.

Examples:

## Critical Identifiers

Missing values in fields such as ProductID may require:

* Row exclusion
* User warning
* Validation failure

depending on severity.

## Optional Categories

Missing values may be replaced with:

`Unknown`

when analytically appropriate.

## Numeric Fields

The system should avoid automatically filling important financial values with arbitrary averages without justification.

Any imputation strategy should be documented.

---

# 13. Outlier Strategy

Outliers should not automatically be deleted.

The system should:

1. Detect unusual values.
2. Flag them.
3. Compare them with business rules.
4. Decide whether they are valid extreme transactions or data errors.

Possible methods:

* IQR
* Z-score for appropriate distributions
* Percentile-based checks
* Domain-specific thresholds

A high-value laptop sale should not be removed simply because it is statistically unusual.

---

# 14. Customer-Level Feature Engineering

For customer segmentation, transaction data will be aggregated into customer-level features.

Core RFM features:

## Recency

Number of days since the customer's latest purchase relative to the dataset reference date.

## Frequency

Number of unique orders made by the customer.

## Monetary

Total revenue contributed by the customer.

Possible additional features:

* Average Order Value
* Total Quantity Purchased
* Category Diversity
* Discount Dependency
* Purchase Interval

Initial MVP segmentation should begin with a simple and explainable feature set.

---

# 15. Forecasting Dataset Preparation

Sales forecasting requires time-ordered aggregated data.

Possible aggregation levels:

* Daily Revenue
* Weekly Revenue
* Monthly Revenue

Preparation steps:

1. Parse and sort dates.
2. Aggregate sales by selected frequency.
3. Identify missing time periods.
4. Handle missing periods appropriately.
5. Preserve chronological order.
6. Create training and validation periods.
7. Evaluate forecasts on future holdout periods.

Random train-test splitting should not be used for time-series forecasting.

---

# 16. Product Intelligence Features

Possible product-level features include:

* Total Revenue
* Total Profit
* Units Sold
* Number of Orders
* Average Selling Price
* Average Discount
* Revenue Growth
* Recent Sales Velocity
* Profit Margin
* Sales Consistency

These features may support product ranking and recommendation logic.

---

# 17. Inventory Intelligence Features

Where stock data is available, useful fields may include:

* Current Stock
* Recent Sales Velocity
* Average Daily Demand
* Forecasted Demand
* Days of Inventory Remaining
* Reorder Risk Indicator

Where stock data is unavailable, recommendations should focus on:

* Demand Growth
* Sales Velocity
* Product Trend
* Relative Demand

The system must clearly distinguish between stock-aware recommendations and demand-only recommendations.

---

# 18. Business Health Score Data Inputs

The Business Health Score may use normalized metrics such as:

* Revenue Growth
* Profit Margin
* Customer Retention Proxy
* Product Performance Balance
* Sales Stability
* Inventory Health, when available

The exact scoring weights will be defined and tested during implementation.

The score calculation should remain transparent and reproducible.

---

# 19. Demo Dataset Design Requirements

The demo dataset should be useful for both analytics and ML demonstrations.

Recommended characteristics:

* At least 12–24 months of transaction history
* Multiple cities
* Multiple product categories
* Multiple brands
* Repeat customers
* Seasonal patterns
* Different product margins
* Varying discount behavior
* Strong and weak products
* Different customer purchase behaviors
* Enough observations for meaningful aggregation

The dataset should not contain personally identifiable customer information.

Synthetic customer IDs should be used.

---

# 20. Data Privacy Principles

RetailPilot AI should follow basic data privacy principles.

The platform should:

* Avoid requiring customer names for analytics.
* Prefer anonymous customer identifiers.
* Avoid unnecessary personal information.
* Process only fields required for business analysis.
* Clearly separate demo data from user-uploaded data.
* Avoid exposing uploaded data publicly.

Future production versions will require stronger security, retention, encryption, and compliance policies.

---

# 21. Example Dataset Row

| OrderID | OrderDate  | CustomerID | ProductID | ProductName  | Category    | Brand        | City  | Quantity | UnitPrice | DiscountPct | UnitCost | PaymentMethod |
| ------- | ---------- | ---------- | --------- | ------------ | ----------- | ------------ | ----- | -------: | --------: | ----------: | -------: | ------------- |
| ORD1001 | 2025-01-05 | CUST104    | P023      | Gaming Mouse | Peripherals | ExampleBrand | Delhi |        2 |      1499 |          10 |      850 | UPI           |

Derived values:

* GrossAmount = 2998
* DiscountAmount = 299.8
* Revenue = 2698.2
* TotalCost = 1700
* Profit = 998.2

---

# 22. Future Data Support

Future versions may support:

* Excel files
* Multiple CSV files
* Database connections
* POS APIs
* E-commerce platform connectors
* Real-time transaction streams
* Supplier data
* Purchase order data
* Return and cancellation data
* Marketing campaign data

These additions should be implemented through modular data connectors.

---

# 23. Dataset Success Criteria

The dataset strategy will be considered successful when:

* The same validated data pipeline supports all MVP modules.
* Calculated KPIs are reproducible.
* Invalid data is clearly reported.
* Customer segmentation uses meaningful customer-level features.
* Forecasting uses proper chronological evaluation.
* Inventory recommendations respect available data limitations.
* Demo Mode produces meaningful and visually understandable results.
* The data model can be extended in future versions.

---

# Conclusion

The dataset is the foundation of RetailPilot AI.

The platform's value depends on reliable validation, transparent cleaning, meaningful feature engineering, and responsible interpretation of results.

The MVP will use a standardized electronics retail schema while maintaining a path toward flexible data mapping and multi-industry support in future versions.
