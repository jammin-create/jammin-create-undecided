//! Build the service

use jade::cjam;

fn main() {
    cjam::build(env!("CARGO_PKG_NAME"), Some(cjam::ModuleType::Service)).ok();
}
