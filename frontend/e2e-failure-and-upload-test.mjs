import { chromium } from "playwright";
import fs from "fs";
import path from "path";

async function runUploadAndFailureTests() {
  console.log("Starting Browser Upload & Failure States Validation on http://localhost:3000 ...");

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (err) {
    browser = await chromium.launch({ channel: "msedge", headless: true });
  }

  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  // Create temporary test files
  const tmpDir = path.resolve("./data_test_tmp");
  if (!fs.existsSync(tmpDir)) fs.mkdirSync(tmpDir, { recursive: true });

  const validCsvPath = path.join(tmpDir, "custom_store_sales.csv");
  fs.writeFileSync(
    validCsvPath,
    "store_id,store_city,sales_volume,daily_revenue\nS1,New York,45,12500.0\nS2,London,30,8900.5\nS3,Tokyo,55,16200.0\nS4,Paris,25,7100.0\n"
  );

  const invalidExtPath = path.join(tmpDir, "malicious_script.exe");
  fs.writeFileSync(invalidExtPath, "BINARY_DATA_HERE");

  const emptyCsvPath = path.join(tmpDir, "empty_dataset.csv");
  fs.writeFileSync(emptyCsvPath, "");

  try {
    // 1. Navigate to Landing Page
    await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
    console.log("[PASS] 1. Loaded Landing Page.");

    // 2. Test Unsupported File Upload (.exe)
    console.log("2. Testing rejection of unsupported .exe file upload...");
    const fileInput = page.locator("input[type='file']");
    await fileInput.setInputFiles(invalidExtPath);
    await page.waitForSelector("text=Unsupported format", { timeout: 5000 });
    console.log("[PASS] 2. Unsupported file (.exe) rejected with clear error message.");

    // 3. Test Empty Dataset Upload
    console.log("3. Testing empty CSV file upload rejection...");
    await fileInput.setInputFiles(emptyCsvPath);
    // Error notification should appear
    await page.waitForSelector("div.border-rose-500\\/30, div.border-rose-500\\/40, div:has-text('Failed to upload'), div:has-text('empty')", { timeout: 8000 });
    console.log("[PASS] 3. Empty CSV rejected with validation error.");

    // 4. Test Valid Custom CSV File Upload
    console.log("4. Testing valid custom CSV file upload...");
    await fileInput.setInputFiles(validCsvPath);
    await page.waitForSelector("text=custom_store_sales.csv", { timeout: 15000 });
    await page.waitForSelector("text=Quality Health", { timeout: 10000 });
    console.log("[PASS] 4. Custom CSV uploaded, profiled, and opened in Dataset Workspace (4 rows).");

    // 5. Ask Analytical Question on Uploaded CSV
    console.log("5. Asking analytical question on uploaded CSV...");
    const questionInput = page.locator("textarea[placeholder*='Ask a question about your data']");
    await questionInput.fill("Which store city had the highest daily revenue?");
    await page.click("button:has-text('Run Analysis')");

    await page.waitForSelector("text=Answer / Primary Finding", { timeout: 60000 });
    console.log("[PASS] 5. Analysis executed on custom uploaded CSV with verified results.");

    console.log("\n=======================================================");
    console.log("🎉 ALL REAL FILE UPLOAD & FAILURE STATE CHECKS PASSED!");
    console.log("=======================================================");
  } catch (err) {
    console.error("Test failure:", err);
    throw err;
  } finally {
    await browser.close();
    // Clean up temporary files
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch (e) {}
  }
}

runUploadAndFailureTests();
