from concurrent.futures import Future
from datetime import datetime, timezone
from itertools import count
from typing import Dict, List, Any, Optional, Tuple


class RuntimeQueue:
    items: List[Dict[str, Any]]
    msg_ids: count[int]

    def __init__(self):
        self.items = []
        self.msg_ids = count(1)


    def enqueue(self, value: Tuple[Any, Optional[Future]]) -> None:
        val, future = value
        msg = {
            "id": next(self.msg_ids),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "value": val
        }
        if future:
            msg["future"] = future

        self.items.append(msg)


    def get_items(self) -> List[Dict[str, Any]]:

        retlist = self.items.copy()

        for msg in retlist:

            if "future" not in msg:
                msg["type"] = "send"
            else:
                msg["type"] = "call"
                future = msg.pop("future")

                if future.done():
                    msg["future_status"] = "failed" if future.exception() else "done"
                else:
                    msg["future_status"] = "not_done"
            retlist.append(msg)

        return retlist


    def clear(self) -> None:
        self.items.clear()
