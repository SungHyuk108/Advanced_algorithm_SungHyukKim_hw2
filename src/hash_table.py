"""A string-keyed hash table using separate chaining."""

from __future__ import annotations

from typing import Iterator


class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key: str, value: object, next_node: _Node | None = None):
        self.key = key
        self.value = value
        self.next = next_node


class _HashTableBase:
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


class HashTable(_HashTableBase):
    """A resizable hash table whose buckets are singly linked lists."""

    def __init__(
        self,
        initial_capacity: int = 8,
        resize_threshold: float | None = 0.75,
    ):
        super().__init__(initial_capacity, resize_threshold)
        self._buckets: list[_Node | None] = [None] * initial_capacity

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


class LinearProbingHashTable(_HashTableBase):
    """A resizable hash table that resolves collisions with linear probing."""

    def __init__(
        self,
        initial_capacity: int = 8,
        resize_threshold: float | None = 0.75,
    ):
        super().__init__(initial_capacity, resize_threshold)
        self._keys: list[str | None] = [None] * initial_capacity
        self._values: list[object | None] = [None] * initial_capacity

    def _find_slot(self, key: str) -> tuple[int | None, int, bool]:
        start = self.bucket_index(key)
        for offset in range(self._capacity):
            index = (start + offset) % self._capacity
            stored_key = self._keys[index]
            if stored_key is None:
                return index, offset + 1, False
            if stored_key == key:
                return index, offset + 1, True
        return None, self._capacity, False

    def put(self, key: str, value: object) -> None:
        self._validate_key(key)
        index, _, found = self._find_slot(key)
        if found:
            self._values[index] = value
            return

        if index is None:
            if self._resize_threshold is None:
                raise OverflowError("hash table is full")
            self._resize(self._capacity * 2)
            index, _, found = self._find_slot(key)
            if found:
                self._values[index] = value
                return

        self._keys[index] = key
        self._values[index] = value
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
        index, probes, found = self._find_slot(key)
        if not found:
            raise KeyError(key)
        return self._values[index], probes

    def contains_key(self, key: str) -> bool:
        self._validate_key(key)
        _, _, found = self._find_slot(key)
        return found

    def bucket_items(self, index: int) -> list[tuple[str, object]]:
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError("bucket index must be an integer")
        if index < 0 or index >= self._capacity:
            raise IndexError(index)
        key = self._keys[index]
        if key is None:
            return []
        return [(key, self._values[index])]

    def items(self) -> Iterator[tuple[str, object]]:
        for index, key in enumerate(self._keys):
            if key is not None:
                yield key, self._values[index]

    def _resize(self, new_capacity: int) -> None:
        old_items = list(self.items())
        self._capacity = new_capacity
        self._size = 0
        self._keys = [None] * new_capacity
        self._values = [None] * new_capacity
        for key, value in old_items:
            index, _, found = self._find_slot(key)
            if found or index is None:
                raise RuntimeError("failed to reinsert key while resizing")
            self._keys[index] = key
            self._values[index] = value
            self._size += 1
