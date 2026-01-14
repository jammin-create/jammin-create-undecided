from aj_lang import service, refine, accumulate, on_transfer
from aj_lang.host import LOG_DEBUG_INT, LOG_DEBUG_STR, get_service_info

@service
class MyService:
    """An empty JAM service."""

    @refine
    def refine(self, item_index: int, service_id: int, payload: bytes, payload_len: int, work_package_hash: bytes) -> bytes:
        """Refine handler."""
        LOG_DEBUG_INT("Example Service Refine", service_id)
        return b"Ok";

    @accumulate
    def accumulate(self, timeslot: int, service_id: int, num_items: int) -> None:
        """Accumulation handler."""
        LOG_DEBUG_INT("Example Service Accumulate", service_id)
        LOG_DEBUG_INT("Balance", get_service_info().balance)
        pass

    @on_transfer
    def on_transfer(self, sender: int, amount: int, memo: bytes) -> None:
        """Transfer handler."""
        try:
            memo_str = memo.decode("utf-8")
        except UnicodeDecodeError:
            memo_str = "???"
        LOG_DEBUG_INT("Received transfer from", sender)
        LOG_DEBUG_INT("Amount", amount)
        LOG_DEBUG_STR("Memo", memo_str)
        pass
