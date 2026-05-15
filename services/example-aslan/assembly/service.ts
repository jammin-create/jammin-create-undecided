import { AccumulateContext, Bytes32, LogMsg, RefineContext } from "@fluffylabs/as-lan";

// LogMsg is a lightweight buffer-based logger that avoids pulling in
// AssemblyScript's String machinery. Use `Logger.create("name")` if you prefer
// template literals at the cost of a larger binary.
const logger: LogMsg = LogMsg.create("svc");

export function accumulate(ptr: u32, len: u32): u64 {
  const ctx = AccumulateContext.create();
  const args = ctx.parseArgs(ptr, len);
  logger.str("Example Service Accumulate, ").u32(args.serviceId).str(" @").u32(args.slot).info();

  const n: u64 = args.argsLength > 0 ? u64(args.argsLength) : 10;
  const fibResult = fibonacci(n);
  logger.str("fibonacci(").u64(n).str(") = ").u64(fibResult).info();

  const raw = new Uint8Array(32);
  for (let i = 0; i < 8; i++) {
    raw[i] = u8((fibResult >> (i * 8)) & 0xff);
  }
  return ctx.yieldHash(Bytes32.wrapUnchecked(raw));
}

export function refine(ptr: u32, len: u32): u64 {
  const ctx = RefineContext.create();
  const args = ctx.parseArgs(ptr, len);
  logger.str("Example Service Refine, ").u32(args.serviceId).info();
  return args.payload.toPtrAndLen();
}

function fibonacci(n: u64): u64 {
  if (n === 0) {
    return 0;
  }

  let a: u64 = 0;
  let b: u64 = 1;
  for (let i: u64 = 0; i < n; i++) {
    const temp = a + b;
    a = b;
    b = temp;
  }
  return a;
}
