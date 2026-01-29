import { test, expect } from '@playwright/test';

test.describe('SAM2 Video Annotator', () => {
  test('should load the application', async ({ page }) => {
    await page.goto('/');

    // Check that the app loads with the correct title
    await expect(page.locator('h1')).toContainText('SAM2 Video Annotator');
  });

  test('should show loading state initially', async ({ page }) => {
    await page.goto('/');

    // Either shows loading or the video selector
    const loadingOrVideos = page.locator('.loading-screen, .video-selector');
    await expect(loadingOrVideos.first()).toBeVisible({ timeout: 10000 });
  });

  test('should display video selector after loading', async ({ page }) => {
    await page.goto('/');

    // Wait for loading to complete and video selector to appear
    const videoSelector = page.locator('.video-selector');
    await expect(videoSelector).toBeVisible({ timeout: 30000 });

    // Check that the "Select a Video" heading is present
    await expect(page.locator('h2')).toContainText('Select a Video');
  });

  test('should show empty state when no videos available', async ({ page }) => {
    await page.goto('/');

    // Wait for video selector
    const videoSelector = page.locator('.video-selector');
    await expect(videoSelector).toBeVisible({ timeout: 30000 });

    // Check for either video cards or empty state
    const videoCards = page.locator('.video-card');
    const emptyState = page.locator('.empty');

    // One of these should be visible
    const hasVideos = await videoCards.count() > 0;
    const isEmpty = await emptyState.isVisible();

    expect(hasVideos || isEmpty).toBeTruthy();
  });

  test('should have status bar with model info', async ({ page }) => {
    await page.goto('/');

    // Wait for status bar to show model status
    const statusBar = page.locator('.status-bar');
    await expect(statusBar).toBeVisible({ timeout: 30000 });

    // Check that model info is displayed
    await expect(statusBar).toContainText('Model:');
  });
});

test.describe('Video Selection', () => {
  test('should handle video click without crashing', async ({ page }) => {
    await page.goto('/');

    // Wait for video selector
    await page.waitForSelector('.video-selector', { timeout: 30000 });

    // Check if there are any video cards
    const videoCards = page.locator('.video-card');
    const count = await videoCards.count();

    if (count > 0) {
      // Click the first video
      await videoCards.first().click();

      // App should not crash - check that either:
      // 1. Workspace appears (video loaded)
      // 2. Loading state appears (extracting frames)
      // 3. Error toast appears (handled error)
      const workspace = page.locator('.workspace');
      const loading = page.locator('.loading');
      const loadingMessage = page.locator('.loading-screen');

      // Wait for one of these states
      await expect(
        workspace.or(loading).or(loadingMessage)
      ).toBeVisible({ timeout: 60000 });

      // Verify the app didn't crash completely
      await expect(page.locator('h1')).toContainText('SAM2 Video Annotator');
    }
  });

  test('should show workspace UI after video loads', async ({ page }) => {
    await page.goto('/');

    // Wait for video selector
    await page.waitForSelector('.video-selector', { timeout: 30000 });

    const videoCards = page.locator('.video-card');
    const count = await videoCards.count();

    if (count > 0) {
      // Click the first video
      await videoCards.first().click();

      // Wait for workspace to appear (may take time for frame extraction)
      const workspace = page.locator('.workspace');
      await expect(workspace).toBeVisible({ timeout: 120000 });

      // Check that key UI elements are present
      await expect(page.locator('.sidebar')).toBeVisible();
      await expect(page.locator('.toolbar')).toBeVisible();
      await expect(page.locator('.video-player')).toBeVisible();
    }
  });

  test('should be able to navigate back to video list', async ({ page }) => {
    await page.goto('/');

    // Wait for video selector
    await page.waitForSelector('.video-selector', { timeout: 30000 });

    const videoCards = page.locator('.video-card');
    const count = await videoCards.count();

    if (count > 0) {
      // Click a video
      await videoCards.first().click();

      // Wait for workspace
      await page.waitForSelector('.workspace', { timeout: 120000 });

      // Click back button
      const backButton = page.locator('button:has-text("Back to Videos")');
      await expect(backButton).toBeVisible();
      await backButton.click();

      // Should show video selector again
      await expect(page.locator('.video-selector')).toBeVisible();
    }
  });
});

test.describe('Annotation Workspace', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.video-selector', { timeout: 30000 });

    const videoCards = page.locator('.video-card');
    const count = await videoCards.count();

    if (count > 0) {
      await videoCards.first().click();
      await page.waitForSelector('.workspace', { timeout: 120000 });
    }
  });

  test('should show object list in sidebar', async ({ page }) => {
    const videoCards = await page.locator('.video-card').count();
    if (videoCards === 0) {
      test.skip();
      return;
    }

    const objectList = page.locator('.object-list');
    await expect(objectList).toBeVisible();

    // Check for add object input
    await expect(page.locator('.add-object input')).toBeVisible();
    await expect(page.locator('.add-object button')).toBeVisible();
  });

  test('should be able to add an object', async ({ page }) => {
    const videoCards = await page.locator('.video-card').count();
    if (videoCards === 0) {
      test.skip();
      return;
    }

    // Type object name
    const input = page.locator('.add-object input');
    await input.fill('Test Object');

    // Click add button
    await page.locator('.add-object button').click();

    // Object should appear in list
    await expect(page.locator('.object-item')).toBeVisible();
    await expect(page.locator('.object-name')).toContainText('Test Object');
  });

  test('should show toolbar with mode buttons', async ({ page }) => {
    const videoCards = await page.locator('.video-card').count();
    if (videoCards === 0) {
      test.skip();
      return;
    }

    const toolbar = page.locator('.toolbar');
    await expect(toolbar).toBeVisible();

    // Check for mode buttons
    await expect(toolbar.locator('button:has-text("Point")')).toBeVisible();
    await expect(toolbar.locator('button:has-text("Box")')).toBeVisible();
  });

  test('should show video player with controls', async ({ page }) => {
    const videoCards = await page.locator('.video-card').count();
    if (videoCards === 0) {
      test.skip();
      return;
    }

    const videoPlayer = page.locator('.video-player');
    await expect(videoPlayer).toBeVisible();

    // Check for canvas
    await expect(videoPlayer.locator('canvas')).toBeVisible();

    // Check for navigation controls
    await expect(page.locator('.nav-controls')).toBeVisible();
  });
});
