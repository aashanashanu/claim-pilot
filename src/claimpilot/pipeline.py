from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable


@dataclass(slots=True)
class Event:
    topic: str
    payload: dict[str, object] = field(default_factory=dict)


Handler = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self.published: list[Event] = []

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers[topic].append(handler)

    def publish(self, event: Event) -> None:
        self.published.append(event)
        for handler in self._handlers.get(event.topic, []):
            handler(event)
