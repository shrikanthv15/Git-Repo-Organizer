import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Auto-cleanup the rendered DOM after every test so React queries
// don't bleed across files.
afterEach(() => {
    cleanup();
});
