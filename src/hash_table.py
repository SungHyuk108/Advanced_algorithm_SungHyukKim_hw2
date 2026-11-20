"""A string-keyed hash table using separate chaining."""

from __future__ import annotations

from typing import Iterator


class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key: str, value: object, next_node: _Node | None = None):
        self.key = key
        self.value = value
        self.next = next_node


class HashTable:
    """A resizable hash table whose buckets are singly linked lists."""

    def __init__(
        self,
        initial_capacity: int = 8,
        resize_threshold: float | None = 0.75,
    ):
        if not isinstance(initial_capacity, int) or isinstance(initial_capacity, bool):
            raise TypeError("initial_capacity must be an integer")
        if initial_capacity < 1:
            raise ValueError("initial_capacity must be positive")
        if resize_threshold is not None and resize_threshold <= 0:
            raise ValueError("resize_threshold must be positive or None")

        self._capacity = initial_capacity
        self._size = 0
        self._resize_threshold = resize_threshold
        self._buckets: list[_Node | None] = [None] * initial_capacity

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return self._size

    def _validate_key(self, key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

    def hash_trace(self, key: str) -> list[tuple[str, int, int]]:
        """Return each Horner step as (character, code point, accumulated hash)."""
        self._validate_key(key)
        accumulated = 0
        trace = []
        for character in key:
            code_point = ord(character)
            accumulated = (accumulated * 31 + code_point) % self._capacity
            trace.append((character, code_point, accumulated))
        return trace

    def bucket_index(self, key: str) -> int:
        trace = self.hash_trace(key)
        return trace[-1][2] if trace else 0

    def put(self, key: str, value: object) -> None:
        self._validate_key(key)
        index = self.bucket_index(key)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        self._buckets[index] = _Node(key, value, self._buckets[index])
        self._size += 1
        if (
            self._resize_threshold is not None
            and self._size / self._capacity > self._resize_threshold
        ):
            self._resize(self._capacity * 2)

    def get(self, key: str) -> object:
        value, _ = self.get_with_probes(key)
        return value

    def get_with_probes(self, key: str) -> tuple[object, int]:
        self._validate_key(key)
        node = self._buckets[self.bucket_index(key)]
        probes = 0
        while node is not None:
            probes += 1
            if node.key == key:
                return node.value, probes
            node = node.next
        raise KeyError(key)

    def contains_key(self, key: str) -> bool:
        self._validate_key(key)
        node = self._buckets[self.bucket_index(key)]
        while node is not None:
            if node.key == key:
                return True
            node = node.next
        return False

    def bucket_items(self, index: int) -> list[tuple[str, object]]:
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError("bucket index must be an integer")
        if index < 0 or index >= self._capacity:
            raise IndexError(index)
        items = []
        node = self._buckets[index]
        while node is not None:
            items.append((node.key, node.value))
            node = node.next
        return items

    def items(self) -> Iterator[tuple[str, object]]:
        for index in range(self._capacity):
            yield from self.bucket_items(index)

    def _resize(self, new_capacity: int) -> None:
        old_items = list(self.items())
        self._capacity = new_capacity
        self._buckets = [None] * new_capacity
        for key, value in old_items:
            index = self.bucket_index(key)
            self._buckets[index] = _Node(key, value, self._buckets[index])
