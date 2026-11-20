"""Compare separate chaining and linear probing on the same random URL keys."""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable, LinearProbingHashTable

CAPACITY = 4093
LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
FAILED_QUERY_COUNT = 10_000
RANDOM_SEED = 8008

RESULTS_PATH = Path(__file__).resolve().with_name("probe_comparison.csv")
SVG_PATH = Path(__file__).resolve().with_name("probe_comparison.svg")


@dataclass(frozen=True)
class ComparisonResult:
    target_alpha: float
    actual_alpha: float
    entries: int
    chaining_success_measured: float
    chaining_success_theory: float
    chaining_failed_measured: float
    chaining_failed_theory: float
    linear_success_measured: float
    linear_success_theory: float
    linear_failed_measured: float
    linear_failed_theory: float


def _random_url(rng: random.Random, host: str, sequence: int) -> str:
    token = rng.getrandbits(128)
    return f"https://{host}/{sequence:06d}-{token:032x}"


def run_comparison() -> list[ComparisonResult]:
    rng = random.Random(RANDOM_SEED)
    chaining = HashTable(initial_capacity=CAPACITY, resize_threshold=None)
    linear = LinearProbingHashTable(initial_capacity=CAPACITY, resize_threshold=None)
    keys: list[str] = []
    results: list[ComparisonResult] = []

    for load_step, target_alpha in enumerate(LOAD_FACTORS):
        target_entries = round(CAPACITY * target_alpha)
        while len(keys) < target_entries:
            key = _random_url(rng, "example.com", len(keys))
            chaining.put(key, key)
            linear.put(key, key)
            keys.append(key)

        if chaining.capacity != CAPACITY or linear.capacity != CAPACITY:
            raise RuntimeError("hash table capacity changed during the comparison")
        if len(chaining) != len(keys) or len(linear) != len(keys):
            raise RuntimeError("the two tables do not contain the same key count")

        chaining_success_total = sum(
            chaining.get_with_probes(key)[1] for key in keys
        )
        linear_success_total = sum(linear.get_with_probes(key)[1] for key in keys)
        chaining_failed_total = 0
        linear_failed_total = 0
        for query_index in range(FAILED_QUERY_COUNT):
            sequence = load_step * FAILED_QUERY_COUNT + query_index
            missing_key = _random_url(rng, "missing.example", sequence)
            chaining_found, _, chaining_probes = chaining.search_with_probes(missing_key)
            linear_found, _, linear_probes = linear.search_with_probes(missing_key)
            if chaining_found or linear_found:
                raise RuntimeError("a failed-search key unexpectedly exists")
            chaining_failed_total += chaining_probes
            linear_failed_total += linear_probes

        alpha = len(keys) / CAPACITY
        results.append(
            ComparisonResult(
                target_alpha=target_alpha,
                actual_alpha=alpha,
                entries=len(keys),
                chaining_success_measured=chaining_success_total / len(keys),
                chaining_success_theory=1 + alpha / 2,
                chaining_failed_measured=chaining_failed_total / FAILED_QUERY_COUNT,
                chaining_failed_theory=alpha,
                linear_success_measured=linear_success_total / len(keys),
                linear_success_theory=0.5 * (1 + 1 / (1 - alpha)),
                linear_failed_measured=linear_failed_total / FAILED_QUERY_COUNT,
                linear_failed_theory=0.5 * (1 + 1 / (1 - alpha) ** 2),
            )
        )

    return results


def _write_csv(results: list[ComparisonResult], path: Path = RESULTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            (
                "target_alpha",
                "actual_alpha",
                "entries",
                "capacity",
                "chaining_success_measured",
                "chaining_success_theory",
                "chaining_failed_measured",
                "chaining_failed_theory",
                "linear_success_measured",
                "linear_success_theory",
                "linear_failed_measured",
                "linear_failed_theory",
                "successful_queries_per_table",
                "failed_queries_per_table",
            )
        )
        for result in results:
            writer.writerow(
                (
                    f"{result.target_alpha:.1f}",
                    f"{result.actual_alpha:.6f}",
                    result.entries,
                    CAPACITY,
                    f"{result.chaining_success_measured:.6f}",
                    f"{result.chaining_success_theory:.6f}",
                    f"{result.chaining_failed_measured:.6f}",
                    f"{result.chaining_failed_theory:.6f}",
                    f"{result.linear_success_measured:.6f}",
                    f"{result.linear_success_theory:.6f}",
                    f"{result.linear_failed_measured:.6f}",
                    f"{result.linear_failed_theory:.6f}",
                    result.entries,
                    FAILED_QUERY_COUNT,
                )
            )


def _draw_panel(
    lines: list[str],
    results: list[ComparisonResult],
    top: int,
    bottom: int,
    y_max: float,
    title: str,
    series: tuple[tuple[str, str, str, list[float]], ...],
) -> None:
    left, right = 95, 1045

    def x_position(alpha: float) -> float:
        return left + (alpha - 0.1) / 0.8 * (right - left)

    def y_position(value: float) -> float:
        return bottom - value / y_max * (bottom - top)

    lines.append(
        f'<text x="{left}" y="{top - 22}" font-size="16" '
        f'font-family="sans-serif">{title}</text>'
    )
    for tick_index in range(6):
        tick = y_max * tick_index / 5
        y = y_position(tick)
        lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" '
            'stroke="#dddddd"/>'
        )
        lines.append(
            f'<text x="{left - 10}" y="{y + 4:.2f}" text-anchor="end" '
            f'font-size="11" font-family="sans-serif">{tick:.1f}</text>'
        )

    for step in range(1, 10):
        alpha = step / 10
        x = x_position(alpha)
        lines.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" '
            'stroke="#eeeeee"/>'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{bottom + 18}" text-anchor="middle" '
            f'font-size="11" font-family="sans-serif">{alpha:.1f}</text>'
        )

    lines.extend(
        (
            f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" '
            'stroke="#222222"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" '
            'stroke="#222222"/>',
        )
    )
    for _, color, dash, values in series:
        points = " ".join(
            f"{x_position(result.target_alpha):.2f},{y_position(value):.2f}"
            for result, value in zip(results, values)
        )
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        lines.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.5"'
            f'{dash_attribute} points="{points}"/>'
        )
        for result, value in zip(results, values):
            lines.append(
                f'<circle cx="{x_position(result.target_alpha):.2f}" '
                f'cy="{y_position(value):.2f}" r="3" fill="{color}"/>'
            )


def _write_svg(results: list[ComparisonResult], path: Path = SVG_PATH) -> None:
    success_max = math.ceil(
        max(
            max(
                result.chaining_success_measured,
                result.chaining_success_theory,
                result.linear_success_measured,
                result.linear_success_theory,
            )
            for result in results
        )
        * 1.1
    )
    failed_max = math.ceil(
        max(
            max(
                result.chaining_failed_measured,
                result.chaining_failed_theory,
                result.linear_failed_measured,
                result.linear_failed_theory,
            )
            for result in results
        )
        * 1.1
    )
    success_series = (
        (
            "Chaining measured",
            "#1769aa",
            "",
            [result.chaining_success_measured for result in results],
        ),
        (
            "Chaining theory",
            "#1769aa",
            "7 5",
            [result.chaining_success_theory for result in results],
        ),
        (
            "Linear probing measured",
            "#c43b3b",
            "",
            [result.linear_success_measured for result in results],
        ),
        (
            "Linear probing theory",
            "#c43b3b",
            "7 5",
            [result.linear_success_theory for result in results],
        ),
    )
    failed_series = (
        (
            "Chaining measured",
            "#1769aa",
            "",
            [result.chaining_failed_measured for result in results],
        ),
        (
            "Chaining theory",
            "#1769aa",
            "7 5",
            [result.chaining_failed_theory for result in results],
        ),
        (
            "Linear probing measured",
            "#c43b3b",
            "",
            [result.linear_failed_measured for result in results],
        ),
        (
            "Linear probing theory",
            "#c43b3b",
            "7 5",
            [result.linear_failed_theory for result in results],
        ),
    )
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="850" '
        'viewBox="0 0 1100 850">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="550" y="32" text-anchor="middle" font-size="20" '
        'font-family="sans-serif">Hash table probe comparison</text>',
        f'<text x="550" y="55" text-anchor="middle" font-size="12" '
        f'font-family="sans-serif">Same {CAPACITY} slots and keys; '
        f'{FAILED_QUERY_COUNT:,} failed queries per load factor</text>',
    ]

    legend_positions = ((95, 82), (355, 82), (615, 82), (875, 82))
    for (label, color, dash, _), (x, y) in zip(success_series, legend_positions):
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        lines.append(
            f'<line x1="{x}" y1="{y}" x2="{x + 28}" y2="{y}" '
            f'stroke="{color}" stroke-width="2.5"{dash_attribute}/>'
        )
        lines.append(
            f'<text x="{x + 35}" y="{y + 4}" font-size="11" '
            f'font-family="sans-serif">{label}</text>'
        )

    _draw_panel(lines, results, 125, 360, success_max, "Successful search", success_series)
    _draw_panel(lines, results, 500, 735, failed_max, "Unsuccessful search", failed_series)
    lines.append(
        '<text x="570" y="785" text-anchor="middle" font-size="13" '
        'font-family="sans-serif">Target load factor (alpha)</text>'
    )
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_table(results: list[ComparisonResult]) -> None:
    print(
        "alpha | chaining success M/T | chaining miss M/T "
        "| linear success M/T | linear miss M/T"
    )
    for result in results:
        print(
            f"{result.actual_alpha:5.3f} | "
            f"{result.chaining_success_measured:6.2f}/{result.chaining_success_theory:6.2f} | "
            f"{result.chaining_failed_measured:6.2f}/{result.chaining_failed_theory:6.2f} | "
            f"{result.linear_success_measured:6.2f}/{result.linear_success_theory:6.2f} | "
            f"{result.linear_failed_measured:6.2f}/{result.linear_failed_theory:6.2f}"
        )


def main() -> None:
    results = run_comparison()
    _write_csv(results)
    _write_svg(results)
    _print_table(results)
    print(f"\nCSV: {RESULTS_PATH}")
    print(f"SVG: {SVG_PATH}")


if __name__ == "__main__":
    main()
