#!/usr/bin/env node

import { setMemory } from "ecalli";
import { memory, runAllTests } from "../build/test.js";

setMemory(memory);
runAllTests();
