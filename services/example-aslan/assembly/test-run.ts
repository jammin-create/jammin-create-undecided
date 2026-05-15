import { runTestSuites, TestSuite } from "@fluffylabs/as-lan/test";
import * as service from "./index.test";

export function runAllTests(): void {
  runTestSuites([TestSuite.create(service.TESTS, "service.ts")]);
}
