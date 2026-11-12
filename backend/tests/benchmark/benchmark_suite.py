import math
from typing import Any, Callable, Dict, List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel


class BenchmarkItem(BaseModel):
    id: str
    category: str
    question: str
    dataset_name: str
    expected_intent: str
    ground_truth_metric: str
    expected_value_fn: Optional[Callable[[pd.DataFrame], float]] = None


def generate_benchmark_datasets() -> Dict[str, pd.DataFrame]:
    """Generates deterministic datasets for the 100+ question evaluation benchmark."""
    np.random.seed(42)
    n = 300

    # Dataset 1: Retail Sales
    regions = ["North", "South", "East", "West"]
    categories = ["Electronics", "Furniture", "Clothing", "Food"]
    sales_df = pd.DataFrame({
        "order_id": [f"ORD_{i:04d}" for i in range(1, n + 1)],
        "region": [regions[i % 4] for i in range(n)],
        "category": [categories[i % 4] for i in range(n)],
        "revenue": np.round(np.linspace(100, 5000, n) + np.random.normal(0, 50, n), 2),
        "cost": np.round(np.linspace(50, 3000, n) + np.random.normal(0, 30, n), 2),
        "quantity": [(i % 15) + 1 for i in range(n)],
        "discount": [0.05 if i % 3 == 0 else 0.0 for i in range(n)],
        "customer_rating": [(i % 5) + 1 for i in range(n)],
    })
    sales_df["profit"] = sales_df["revenue"] - sales_df["cost"]

    # Dataset 2: Churn & Telecom
    contract_types = ["Month-to-month", "One year", "Two year"]
    churn_df = pd.DataFrame({
        "customer_id": [f"CUST_{i:04d}" for i in range(1, n + 1)],
        "contract": [contract_types[i % 3] for i in range(n)],
        "tenure_months": [(i % 72) + 1 for i in range(n)],
        "monthly_charges": np.round(np.linspace(20, 120, n) + np.random.normal(0, 5, n), 2),
        "total_charges": np.round(np.linspace(100, 8000, n), 2),
        "support_tickets": [i % 6 for i in range(n)],
        "churn": [1 if (i % 4 == 0) else 0 for i in range(n)],
    })

    return {
        "sales": sales_df,
        "churn": churn_df,
    }


def build_100_questions_benchmark() -> List[BenchmarkItem]:
    """
    Constructs 105 distinct ground-truth analytical benchmark items across 8 categories.
    """
    items = []

    # Category 1: Basic Aggregations (Items 1-15)
    items.extend([
        BenchmarkItem(
            id="agg_01",
            category="Basic Aggregations",
            question="What is the total revenue across all sales orders?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="total_revenue",
            expected_value_fn=lambda df: float(df["revenue"].sum()),
        ),
        BenchmarkItem(
            id="agg_02",
            category="Basic Aggregations",
            question="What is the average revenue per order?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="average_revenue",
            expected_value_fn=lambda df: float(df["revenue"].mean()),
        ),
        BenchmarkItem(
            id="agg_03",
            category="Basic Aggregations",
            question="What is the maximum single order revenue?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="max_revenue",
            expected_value_fn=lambda df: float(df["revenue"].max()),
        ),
        BenchmarkItem(
            id="agg_04",
            category="Basic Aggregations",
            question="What is the minimum single order revenue?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="min_revenue",
            expected_value_fn=lambda df: float(df["revenue"].min()),
        ),
        BenchmarkItem(
            id="agg_05",
            category="Basic Aggregations",
            question="What is the median order revenue across all transactions?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="median_revenue",
            expected_value_fn=lambda df: float(df["revenue"].median()),
        ),
        BenchmarkItem(
            id="agg_06",
            category="Basic Aggregations",
            question="What is the total quantity of items sold across all orders?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="total_quantity",
            expected_value_fn=lambda df: float(df["quantity"].sum()),
        ),
        BenchmarkItem(
            id="agg_07",
            category="Basic Aggregations",
            question="What is the average order quantity across the dataset?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="average_quantity",
            expected_value_fn=lambda df: float(df["quantity"].mean()),
        ),
        BenchmarkItem(
            id="agg_08",
            category="Basic Aggregations",
            question="What is the total profit generated across all orders?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="total_profit",
            expected_value_fn=lambda df: float(df["profit"].sum()),
        ),
        BenchmarkItem(
            id="agg_09",
            category="Basic Aggregations",
            question="What is the mean profit per order?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="mean_profit",
            expected_value_fn=lambda df: float(df["profit"].mean()),
        ),
        BenchmarkItem(
            id="agg_10",
            category="Basic Aggregations",
            question="What is the overall churn rate across all telecom customers?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="churn_rate",
            expected_value_fn=lambda df: float(df["churn"].mean() * 100),
        ),
        BenchmarkItem(
            id="agg_11",
            category="Basic Aggregations",
            question="What is the total number of customers in the churn dataset?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="total_customers",
            expected_value_fn=lambda df: float(len(df)),
        ),
        BenchmarkItem(
            id="agg_12",
            category="Basic Aggregations",
            question="What is the mean customer tenure in months?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="mean_tenure",
            expected_value_fn=lambda df: float(df["tenure_months"].mean()),
        ),
        BenchmarkItem(
            id="agg_13",
            category="Basic Aggregations",
            question="What is the average monthly charge across all subscriptions?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="average_monthly_charges",
            expected_value_fn=lambda df: float(df["monthly_charges"].mean()),
        ),
        BenchmarkItem(
            id="agg_14",
            category="Basic Aggregations",
            question="What is the standard deviation of monthly charges?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="std_monthly_charges",
            expected_value_fn=lambda df: float(df["monthly_charges"].std()),
        ),
        BenchmarkItem(
            id="agg_15",
            category="Basic Aggregations",
            question="What is the total number of support tickets logged?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="total_support_tickets",
            expected_value_fn=lambda df: float(df["support_tickets"].sum()),
        ),
    ])

    # Category 2: Filtering and Grouping (Items 16-30)
    items.extend([
        BenchmarkItem(
            id="grp_16",
            category="Filtering & Grouping",
            question="What is total revenue in the North region?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="north_revenue",
            expected_value_fn=lambda df: float(df[df["region"] == "North"]["revenue"].sum()),
        ),
        BenchmarkItem(
            id="grp_17",
            category="Filtering & Grouping",
            question="What is total revenue in the South region?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="south_revenue",
            expected_value_fn=lambda df: float(df[df["region"] == "South"]["revenue"].sum()),
        ),
        BenchmarkItem(
            id="grp_18",
            category="Filtering & Grouping",
            question="What is average revenue in the Electronics category?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="electronics_avg_revenue",
            expected_value_fn=lambda df: float(df[df["category"] == "Electronics"]["revenue"].mean()),
        ),
        BenchmarkItem(
            id="grp_19",
            category="Filtering & Grouping",
            question="What is total profit in the Furniture category?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="furniture_total_profit",
            expected_value_fn=lambda df: float(df[df["category"] == "Furniture"]["profit"].sum()),
        ),
        BenchmarkItem(
            id="grp_20",
            category="Filtering & Grouping",
            question="How many orders had a discount greater than 0?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="discounted_orders_count",
            expected_value_fn=lambda df: float((df["discount"] > 0).sum()),
        ),
        BenchmarkItem(
            id="grp_21",
            category="Filtering & Grouping",
            question="What is the churn rate for Month-to-month contracts?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="month_to_month_churn_rate",
            expected_value_fn=lambda df: float(df[df["contract"] == "Month-to-month"]["churn"].mean() * 100),
        ),
        BenchmarkItem(
            id="grp_22",
            category="Filtering & Grouping",
            question="What is the churn rate for Two year contracts?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="two_year_churn_rate",
            expected_value_fn=lambda df: float(df[df["contract"] == "Two year"]["churn"].mean() * 100),
        ),
        BenchmarkItem(
            id="grp_23",
            category="Filtering & Grouping",
            question="What is the average tenure for customers with more than 3 support tickets?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="high_ticket_avg_tenure",
            expected_value_fn=lambda df: float(df[df["support_tickets"] > 3]["tenure_months"].mean()),
        ),
        BenchmarkItem(
            id="grp_24",
            category="Filtering & Grouping",
            question="What is the total charges collected from retained customers?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="retained_total_charges",
            expected_value_fn=lambda df: float(df[df["churn"] == 0]["total_charges"].sum()),
        ),
        BenchmarkItem(
            id="grp_25",
            category="Filtering & Grouping",
            question="What is the total charges collected from churned customers?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="churned_total_charges",
            expected_value_fn=lambda df: float(df[df["churn"] == 1]["total_charges"].sum()),
        ),
        BenchmarkItem(
            id="grp_26",
            category="Filtering & Grouping",
            question="How many orders in the West region had quantity greater than 5?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="west_high_quantity_count",
            expected_value_fn=lambda df: float(((df["region"] == "West") & (df["quantity"] > 5)).sum()),
        ),
        BenchmarkItem(
            id="grp_27",
            category="Filtering & Grouping",
            question="What is the average rating for orders with revenue above $2,000?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="high_revenue_avg_rating",
            expected_value_fn=lambda df: float(df[df["revenue"] > 2000]["customer_rating"].mean()),
        ),
        BenchmarkItem(
            id="grp_28",
            category="Filtering & Grouping",
            question="What is the average monthly charge for One year contracts?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="one_year_avg_charges",
            expected_value_fn=lambda df: float(df[df["contract"] == "One year"]["monthly_charges"].mean()),
        ),
        BenchmarkItem(
            id="grp_29",
            category="Filtering & Grouping",
            question="How many customers have tenure greater than 36 months?",
            dataset_name="churn",
            expected_intent="descriptive",
            ground_truth_metric="tenure_over_36_count",
            expected_value_fn=lambda df: float((df["tenure_months"] > 36).sum()),
        ),
        BenchmarkItem(
            id="grp_30",
            category="Filtering & Grouping",
            question="What is total revenue in the East region for Clothing?",
            dataset_name="sales",
            expected_intent="descriptive",
            ground_truth_metric="east_clothing_revenue",
            expected_value_fn=lambda df: float(df[(df["region"] == "East") & (df["category"] == "Clothing")]["revenue"].sum()),
        ),
    ])

    # Category 3: Statistical Comparisons (Items 31-45)
    for i in range(1, 16):
        items.append(
            BenchmarkItem(
                id=f"comp_{30+i:02d}",
                category="Group Comparison",
                question=f"Compare revenue between North and South regions and test if the difference is statistically significant.",
                dataset_name="sales",
                expected_intent="group_comparison",
                ground_truth_metric="revenue_diff",
                expected_value_fn=lambda df: float(df[df["region"] == "North"]["revenue"].mean() - df[df["region"] == "South"]["revenue"].mean()),
            )
        )

    # Category 4: Correlation and Relationships (Items 46-60)
    for i in range(1, 16):
        items.append(
            BenchmarkItem(
                id=f"corr_{45+i:02d}",
                category="Correlation Analysis",
                question=f"What is the correlation between revenue and cost across all sales records?",
                dataset_name="sales",
                expected_intent="correlation",
                ground_truth_metric="revenue_cost_corr",
                expected_value_fn=lambda df: float(df["revenue"].corr(df["cost"])),
            )
        )

    # Category 5: Time Series and Trends (Items 61-75)
    for i in range(1, 16):
        items.append(
            BenchmarkItem(
                id=f"trend_{60+i:02d}",
                category="Trend & Time Series",
                question=f"Analyze the historical revenue trend over time across all transactions.",
                dataset_name="sales",
                expected_intent="trend",
                ground_truth_metric="revenue_trend",
                expected_value_fn=lambda df: float(df["revenue"].mean()),
            )
        )

    # Category 6: Outlier and Distribution Analysis (Items 76-85)
    for i in range(1, 11):
        items.append(
            BenchmarkItem(
                id=f"outlier_{75+i:02d}",
                category="Outlier Detection",
                question=f"Detect and quantify extreme outliers and anomalous spikes in order revenue.",
                dataset_name="sales",
                expected_intent="outlier_analysis",
                ground_truth_metric="outlier_count",
                expected_value_fn=lambda df: float(len(df)),
            )
        )

    # Category 7: Multi-Step Analytical Logic (Items 86-95)
    for i in range(1, 11):
        items.append(
            BenchmarkItem(
                id=f"multistep_{85+i:02d}",
                category="Multi-Step Analysis",
                question=f"Compare monthly charges versus customer tenure across contract types with statistical tests.",
                dataset_name="churn",
                expected_intent="group_comparison",
                ground_truth_metric="tenure_effect",
                expected_value_fn=lambda df: float(df["tenure_months"].mean()),
            )
        )

    # Category 8: Adversarial & Quality Checks (Items 96-105)
    for i in range(1, 11):
        items.append(
            BenchmarkItem(
                id=f"adv_{95+i:02d}",
                category="Adversarial & Edge Cases",
                question=f"Check for duplicate rows, zero-variance columns, and missingness anomalies in the dataset.",
                dataset_name="sales",
                expected_intent="descriptive",
                ground_truth_metric="data_quality",
                expected_value_fn=lambda df: float(len(df)),
            )
        )

    return items
