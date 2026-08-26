import { describe, expect, test } from "vitest";
import { normalizeApiBaseUrl } from "./api";

describe("normalizeApiBaseUrl", () => {
  test("keeps absolute URLs and removes trailing slashes", () => {
    expect(normalizeApiBaseUrl("https://be5g-sp-api-production.up.railway.app/")).toBe(
      "https://be5g-sp-api-production.up.railway.app"
    );
    expect(normalizeApiBaseUrl("http://localhost:8000/")).toBe("http://localhost:8000");
  });

  test("adds https to bare deployed hostnames", () => {
    expect(normalizeApiBaseUrl("be5g-sp-api-production.up.railway.app")).toBe(
      "https://be5g-sp-api-production.up.railway.app"
    );
  });

  test("keeps intentional relative base paths", () => {
    expect(normalizeApiBaseUrl("/api/")).toBe("/api");
  });
});
