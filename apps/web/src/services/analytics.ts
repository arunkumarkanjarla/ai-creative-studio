import { apiRequest } from "./api";

/**
 * Track a page visit/route change
 * Works for both logged-in and logged-out users
 */
export async function trackPageView(path: string): Promise<void> {
  try {
    await apiRequest("/analytics/track", {
      method: "POST",
      body: JSON.stringify({
        path,
        action: "page_view",
      }),
    });
  } catch (error) {
    // Silently fail - don't break the app if analytics fails
    console.error("Analytics tracking failed:", error);
  }
}
