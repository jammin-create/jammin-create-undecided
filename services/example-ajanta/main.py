from aj_lang import service, refine, accumulate, on_transfer
from aj_lang.host import LOG_INFO, get_service_info

@service
class MyService:
    """An empty JAM service."""

    @refine
    def refine(self, item_index: int, service_id: int, payload: bytes, payload_len: int, work_package_hash: bytes) -> bytes:
        """Refine handler."""
        LOG_INFO("Example Service Refine, " + service_id)
        return b"Ok";

    @accumulate
    def accumulate(self, slot: int, service_id: int, n_items: int) -> None:
        """Accumulation handler."""
        LOG_INFO("Example Service Accumulate " + service_id + ", " + get_service_info().balance)
        pass

    @on_transfer
    def on_transfer(self, sender: int, amount: int, memo: bytes) -> None:
        """Transfer handler."""
        try:
            memo_str = memo.decode("utf-8")
        except UnicodeDecodeError:
            memo_str = "???"
        LOG_INFO("Received transfer from " + sender + " of " + amount + " with memo: " + memo_str)
        pass
