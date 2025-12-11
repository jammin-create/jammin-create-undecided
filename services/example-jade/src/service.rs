//! Empty JADE service

use jade::{
    info,
    prelude::Vec,
    service::{
        OpaqueHash,
        vm::{AccumulateItem},
    },
};

#[jade::refine]
fn refine(
    _core: u16,
    _index: u16,
    service_id: u32,
    payload: Vec<u8>,
    _package_hash: OpaqueHash,
) -> Vec<u8> {
    info!("Empty Service Refine, {service_id:x}h");
    payload
}

#[jade::accumulate]
fn accumulate(now: u32, id: u32, items: Vec<AccumulateItem>) -> Option<OpaqueHash> {
    info!(
        "Empty Service Accumulate, {id:x}h @{now} items: ${}",
        items.len()
    );
    None
}
