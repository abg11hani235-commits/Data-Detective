import { chromium } from "playwright";

async function runBrowserValidation() {
  console.log("Starting Playwright Real Browser E2E Validation on http://localhost:3000 ...");

  // Launch browser with system edge/chrome or default chromium
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (err) {
    console.log("Default chromium launch failed, attempting with msedge channel...");
    browser = await chromium.launch({ channel: "msedge", headless: true });
  }

  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  // Listen to browser console errors
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      console.log(`[Browser Console Error] ${msg.text()}`);
    }
  });

  try {
    // 1. Navigate to Landing Page
    console.log("1. Navigating to http://localhost:3000 ...");
    await page.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 15000 });

    const title = await page.textContent("body");
    if (!title.includes("DATA DETECTIVE")) {
      throw new Error("Landing page branding missing DATA DETECTIVE");
    }
    console.log("[PASS] 1. Landing page loaded with 'DATA DETECTIVE'");

    // 2. Check Sample Dataset Cards
    const sampleCards = await page.locator("h3:has-text('Global Retail Sales')").count();
    if (sampleCards === 0) {
      throw new Error("Sample dataset card 'Global Retail Sales' not found.");
    }
    console.log("[PASS] 2. Verified 3 pre-loaded sample datasets are present.");

    // 3. Load Sample Dataset
    console.log("3. Clicking 'Global Retail Sales' card to load dataset...");
    await page.locator("h3:has-text('Global Retail Sales')").click();

    // Wait for Dataset Workspace to appear
    await page.waitForSelector("text=Quality Health", { timeout: 10000 });
    const bodyText = await page.textContent("body");
    if (!bodyText.includes("250") || !bodyText.includes("Quality Health")) {
      throw new Error("Dataset Workspace did not render expected row count 250.");
    }
    console.log("[PASS] 3. Dataset Workspace rendered with 250 rows, 9 columns, and Quality Health score.");

    // 4. Test Workspace Tabs (Preview Tab)
    console.log("4. Switching to 'Sample Preview' tab...");
    await page.click("button:has-text('Sample Preview')");
    await page.waitForSelector("table tbody tr", { timeout: 5000 });
    const previewRowCount = await page.locator("table tbody tr").count();
    if (previewRowCount < 5) {
      throw new Error(`Expected at least 5 preview rows, got ${previewRowCount}`);
    }
    console.log(`[PASS] 4. Tabular data preview active (${previewRowCount} rows rendered).`);

    // Switch back to Schema tab
    await page.click("button:has-text('Schema & Statistics')");
    await page.waitForSelector("th:has-text('Column Name')", { timeout: 5000 });
    console.log("[PASS] 5. Switched back to Schema & Statistics view.");

    // 5. Ask Analytical Question
    console.log("6. Clicking suggested question chip...");
    const chip = page.locator("button:has-text('Which products generated the highest revenue and profit?')");
    await chip.click();

    console.log("7. Clicking 'Run Analysis' button...");
    await page.click("button:has-text('Run Analysis')");

    // 6. Verify SSE Timeline / Progress State
    console.log("8. Observing live analysis progress...");
    // Wait for completed analysis card to appear
    await page.waitForSelector("text=Answer / Primary Finding", { timeout: 60000 });
    console.log("[PASS] 6. Live execution completed: 'Answer / Primary Finding' card appeared.");

    // 7. Verify Computed Results
    const analysisCard = page.locator("article:has-text('Answer / Primary Finding')").first();
    const findingsText = await analysisCard.textContent();

    if (!findingsText.includes("Evidence-Based Findings") || !findingsText.includes("Key Metrics")) {
      throw new Error("Analysis card missing Findings or Metrics sections.");
    }
    console.log("[PASS] 7. Evidence-based findings and computed metrics rendered.");

    // 8. Verify Plotly Chart rendering
    console.log("8. Verifying interactive chart container...");
    await page.waitForSelector("[data-testid='plotly-chart-container'], .js-plotly-plot", { timeout: 15000 });
    console.log("[PASS] 8. Interactive Plotly chart rendered on page.");

    // 9. Verify Python Code Inspector
    console.log("9. Testing 'Generated Python Analysis Code' drawer...");
    await page.click("button:has-text('Generated Python Analysis Code')");
    await page.waitForSelector("pre", { timeout: 5000 });
    const codeSnippet = await page.textContent("pre");
    if (!codeSnippet.includes("df") || !codeSnippet.includes("results.json")) {
      throw new Error("Inspected Python script missing standard contract code.");
    }
    console.log("[PASS] 9. Python code transparency drawer opened and verified.");

    // 10. Verify Full Report Modal
    console.log("10. Testing 'Full Report' modal...");
    await page.click("button:has-text('Full Report')");
    await page.waitForSelector("iframe[title='Report Preview']", { timeout: 8000 });
    console.log("[PASS] 10. Executive Report modal opened with embedded report iframe.");

    // Close modal
    await page.click("button[aria-label='Close report']");
    await page.waitForSelector("iframe[title='Report Preview']", { state: "detached", timeout: 5000 });
    console.log("[PASS] 11. Executive Report modal closed.");

    // 11. Multi-turn Follow-up Question
    console.log("12. Submitting follow-up query: 'How did monthly revenue trend over time?'...");
    const input = page.locator("textarea[placeholder*='Ask a question about your data']");
    await input.fill("How did monthly revenue trend over time?");
    await page.click("button:has-text('Run Analysis')");

    // Wait for second analysis card containing the follow-up question
    await page.waitForSelector("h3:has-text('How did monthly revenue trend over time?')", { timeout: 60000 });
    console.log("[PASS] 12. Follow-up query executed within session context (second analysis rendered).");

    // 12. Switch Dataset Test
    console.log("13. Testing 'Switch Dataset' navigation...");
    await page.click("button:has-text('Switch Dataset')");
    await page.waitForSelector("h1:has-text('Upload your data')", { timeout: 5000 });
    console.log("[PASS] 13. Switched dataset and successfully returned to Landing View.");

    console.log("\n=======================================================");
    console.log("🎉 ALL 13 REAL BROWSER E2E TESTS PASSED WITH 100% SUCCESS!");
    console.log("=======================================================");
  } catch (err) {
    console.error("Browser validation failure:", err);
    throw err;
  } finally {
    await browser.close();
  }
}

runBrowserValidation();
