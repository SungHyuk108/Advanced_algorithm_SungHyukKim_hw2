"""Measure separate-chaining search costs and compare them with theory."""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable

CAPACITY = 4093
LOAD_FACTORS = tuple(step / 4 for step in range(1, 17))
FAILED_QUERY_COUNT = 10_000
RANDOM_SEED = 20261120

RESULTS_PATH = Path(__file__).resolve().with_name("results.csv")
SVG_PATH = Path(__file__).resolve().with_name("probe_experiment.svg")


@dataclass(frozen=True)
class ExperimentResult:
    target_alpha: float
    alpha: float
    entries: int
    successful_measured: float
    successful_theory: float
    failed_measured: float
    failed_theory: float


def _random_url(rng: random.Random, host: str, sequence: int) -> str:
    token = rng.getrandbits(128)
    return f"https://{host}/{sequence:06d}-{token:032x}"


def _unsuccessful_probe_count(table: HashTable, key: str) -> int:
    if table.contains_key(key):
        raise ValueError("unsuccessful search key is already in the table")
    return len(table.bucket_items(table.bucket_index(key)))


def run_experiment() -> list[ExperimentResult]:
    rng = random.Random(RANDOM_SEED)
    table = HashTable(initial_capacity=CAPACITY, resize_threshold=None)
    urls: list[str] = []
    results: list[ExperimentResult] = []

    for load_step, target_alpha in enumerate(LOAD_FACTORS):
        target_entries = round(CAPACITY * target_alpha)
        while len(urls) < target_entries:
            url = _random_url(rng, "example.com", len(urls))
            table.put(url, url)
            urls.append(url)

        if table.capacity != CAPACITY:
            raise RuntimeError("hash table capacity changed during the experiment")

        successful_probe_total = sum(
            table.get_with_probes(url)[1] for url in urls
        )
        failed_probe_total = 0
        for query_index in range(FAILED_QUERY_COUNT):
            sequence = load_step * FAILED_QUERY_COUNT + query_index
            missing_url = _random_url(rng, "missing.example", sequence)
            failed_probe_total += _unsuccessful_probe_count(table, missing_url)

        alpha = len(table) / table.capacity
        results.append(
            ExperimentResult(
                target_alpha=target_alpha,
                alpha=alpha,
                entries=len(table),
                successful_measured=successful_probe_total / len(urls),
                successful_theory=1 + alpha / 2,
                failed_measured=failed_probe_total / FAILED_QUERY_COUNT,
                failed_theory=alpha,
            )
        )

    return results


def _write_csv(results: list[ExperimentResult], path: Path = RESULTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            (
                "target_alpha",
                "actual_alpha",
                "entries",
                "capacity",
                "successful_measured_nodes",
                "successful_theoretical_nodes",
                "failed_measured_nodes",
                "failed_theoretical_nodes",
                "successful_queries",
                "failed_queries",
            )
        )
        for result in results:
            writer.writerow(
                (
                    f"{result.target_alpha:.2f}",
                    f"{result.alpha:.6f}",
                    result.entries,
                    CAPACITY,
                    f"{result.successful_measured:.6f}",
                    f"{result.successful_theory:.6f}",
                    f"{result.failed_measured:.6f}",
                    f"{result.failed_theory:.6f}",
                    result.entries,
                    FAILED_QUERY_COUNT,
                )
            )


def _write_svg(results: list[ExperimentResult], path: Path = SVG_PATH) -> None:
    width, height = 1000, 620
    left, right, top, bottom = 85, 745, 85, 520
    maximum = max(
        max(result.successful_measured, result.successful_theory,
            result.failed_measured, result.failed_theory)
        for result in results
    )
    y_max = max(1, math.ceil(maximum * 1.1))

    def x_position(alpha: float) -> float:
        return left + (alpha - 0.25) / (4 - 0.25) * (right - left)

    def y_position(value: float) -> float:
        return bottom - value / y_max * (bottom - top)

    series = (
        (
            "Successful (measured)",
            "#1769aa",
            "",
            [result.successful_measured for result in results],
        ),
        (
            "Successful (theory: 1 + alpha/2)",
            "#1769aa",
            "7 5",
            [result.successful_theory for result in results],
        ),
        (
            "Failed (measured)",
            "#c43b3b",
            "",
            [result.failed_measured for result in results],
        ),
        (
            "Failed (theory: alpha)",
            "#c43b3b",
            "7 5",
            [result.failed_theory for result in results],
        ),
    )

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="500" y="35" text-anchor="middle" font-size="20" '
        'font-family="sans-serif">Separate chaining: measured and theoretical probes</text>',
        f'<text x="500" y="58" text-anchor="middle" font-size="12" '
        f'font-family="sans-serif">Capacity {CAPACITY}; '
        f'{FAILED_QUERY_COUNT:,} failed queries per load factor; seed {RANDOM_SEED}</text>',
    ]

    for tick in range(y_max + 1):
        y = y_position(tick)
        lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" '
            'stroke="#dddddd"/>'
        )
        lines.append(
            f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" '
            f'font-size="12" font-family="sans-serif">{tick}</text>'
        )

    x_ticks = (0.25, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)
    for tick in x_ticks:
        x = x_position(tick)
        lines.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" '
            'stroke="#eeeeee"/>'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{bottom + 22}" text-anchor="middle" '
            f'font-size="12" font-family="sans-serif">{tick:g}</text>'
        )

    lines.extend(
        (
            f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" '
            'stroke="#222222"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" '
            'stroke="#222222"/>',
            f'<text x="{(left + right) / 2}" y="{bottom + 55}" text-anchor="middle" '
            'font-size="14" font-family="sans-serif">Target load factor (alpha)</text>',
            f'<text x="22" y="{(top + bottom) / 2}" text-anchor="middle" '
            'font-size="14" font-family="sans-serif" '
            f'transform="rotate(-90 22 {(top + bottom) / 2})">Average nodes visited</text>',
        )
    )

    for series_index, (label, color, dash, values) in enumerate(series):
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
                f'cy="{y_position(value):.2f}" r="2.8" fill="{color}"/>'
            )
        legend_y = 120 + series_index * 28
        lines.append(
            f'<line x1="775" y1="{legend_y}" x2="810" y2="{legend_y}" '
            f'stroke="{color}" stroke-width="2.5"{dash_attribute}/>'
        )
        lines.append(
            f'<text x="818" y="{legend_y + 5}" font-size="12" '
            f'font-family="sans-serif">{label}</text>'
        )

    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_table(results: list[ExperimentResult]) -> None:
    print(
        f"capacity={CAPACITY}, seed={RANDOM_SEED}, "
        f"failed queries per load factor={FAILED_QUERY_COUNT}"
    )
    print(
        "target alpha | actual alpha | entries | success measured/theory "
        "| failed measured/theory"
    )
    for result in results:
        print(
            f"{result.target_alpha:11.2f} | {result.alpha:11.6f} | "
            f"{result.entries:7d} | {result.successful_measured:7.3f} / "
            f"{result.successful_theory:7.3f} | {result.failed_measured:7.3f} / "
            f"{result.failed_theory:7.3f}"
        )


def main() -> None:
    results = run_experiment()
    _write_csv(results)
    _write_svg(results)
    _print_table(results)
    print(f"\nCSV: {RESULTS_PATH}")
    print(f"SVG: {SVG_PATH}")


if __name__ == "__main__":
    main()
