module my_service;

import jam::types;
import jam::refine;
import jam::accumulate;
import jam::log;

fn types::RefineResult refine(refine::Ctx* ctx) @export("refine")
{
  log::info("svc", "Hello from refine!");

  static char[5] result = { 'h', 'e', 'l', 'l', 'o' };
  return ctx.result_ok(&result, 5);
}

fn void accumulate(accumulate::Ctx* ctx) @export("accumulate")
{
  log::info("svc", "Hello from accumulate!");
}
