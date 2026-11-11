import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


def generate_samples(base_dir: Path):
    base_dir.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    # 1. Sales Dataset (200 records)
    sales_file = base_dir / "sales.csv"
    products = [
        ("Quantum Laptop", "Electronics", 1200.0, 850.0),
        ("Apex Smartphone", "Electronics", 800.0, 520.0),
        ("ErgoFit Desk Chair", "Furniture", 350.0, 190.0),
        ("Lumina Floor Lamp", "Furniture", 110.0, 60.0),
        ("Trailblazer Backpack", "Accessories", 85.0, 35.0),
        ("Aero Noise-Canceling Buds", "Audio", 180.0, 95.0),
        ("Titan Mechanical Keyboard", "Electronics", 140.0, 75.0),
    ]
    regions = ["North America", "Europe", "Asia Pacific", "Latin America"]
    start_date = datetime(2025, 1, 1)

    with open(sales_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "product", "category", "region", "quantity", "unit_price", "revenue", "cost", "profit"])
        for i in range(250):
            p_name, cat, price, unit_cost = random.choice(products)
            region = random.choice(regions)
            # Add regional volume tilt
            qty = random.randint(1, 15) if region == "North America" else random.randint(1, 10)
            date = (start_date + timedelta(days=random.randint(0, 360))).strftime("%Y-%m-%d")
            revenue = round(qty * price, 2)
            cost = round(qty * unit_cost, 2)
            profit = round(revenue - cost, 2)
            writer.writerow([date, p_name, cat, region, qty, price, revenue, cost, profit])

    # 2. Customer Churn Dataset (200 records)
    churn_file = base_dir / "customer_churn.csv"
    contracts = ["Month-to-month", "One year", "Two year"]

    with open(churn_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["customer_id", "age", "tenure", "monthly_charges", "contract", "support_calls", "churn"])
        for i in range(200):
            cid = f"CUST-{1000 + i}"
            age = random.randint(18, 70)
            contract = random.choice(contracts)
            tenure = random.randint(1, 12) if contract == "Month-to-month" else random.randint(12, 60)
            charges = round(random.uniform(30.0, 115.0), 2)
            
            # Realistic churn tendency
            calls = random.randint(0, 6)
            churn_prob = 0.15
            if contract == "Month-to-month":
                churn_prob += 0.25
            if calls >= 4:
                churn_prob += 0.35
            if charges > 85.0:
                churn_prob += 0.15
            
            churn = "Yes" if random.random() < churn_prob else "No"
            writer.writerow([cid, age, tenure, charges, contract, calls, churn])

    # 3. Student Performance Dataset (200 records)
    student_file = base_dir / "student_performance.csv"
    with open(student_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["student_id", "study_hours", "attendance_pct", "assignments_score", "midterm_score", "final_score"])
        for i in range(200):
            sid = f"STU-{500 + i}"
            study_hours = round(random.uniform(5.0, 35.0), 1)
            attendance = round(random.uniform(60.0, 100.0), 1)
            # Realistic scores correlated with study hours & attendance
            base_perf = (study_hours * 1.5) + (attendance * 0.3) + random.uniform(-8.0, 8.0)
            assignments = max(40.0, min(100.0, round(base_perf + random.uniform(-5, 5), 1)))
            midterm = max(35.0, min(100.0, round(base_perf + random.uniform(-8, 8), 1)))
            final = max(30.0, min(100.0, round(0.5 * midterm + 0.3 * assignments + (study_hours * 0.5) + random.uniform(-4, 4), 1)))
            writer.writerow([sid, study_hours, attendance, assignments, midterm, final])

    print("Sample datasets generated successfully.")


if __name__ == "__main__":
    generate_samples(Path(__file__).resolve().parent / "samples")
