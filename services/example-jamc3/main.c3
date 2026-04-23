module my_service;

import jam::types;
import jam::service;
import jam::log;

fn void refine(types::RefineArgs* args) @export("refine")
{
  log::info("svc", "Hello from refine!");

  char[5] result = { 'h', 'e', 'l', 'l', 'o' };
  service::return_to_host(&result, 5);
}

fn void accumulate(types::AccumulateArgs* args) @export("accumulate")
{
  log::info("svc", "Hello from accumulate!");
}
