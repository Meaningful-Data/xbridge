"""
Performance test for filing indicator validation
Measures memory usage and execution time with and without validation
"""

import time
import tracemalloc
from pathlib import Path
from tempfile import TemporaryDirectory

from xbridge.api import convert_instance

# Test files to use for performance testing
TEST_FILES = [
    Path(__file__).parent / "test_files" / "sample_3_2_phase3" / "test2_in.xbrl",  # Large file
    Path(__file__).parent / "test_files" / "sample_3_2_phase3" / "test5_in.xbrl",  # Very large file
]


def measure_performance(instance_path: Path, validate: bool) -> tuple[float, float, int]:
    """
    Measure performance of conversion.

    Returns:
        tuple: (execution_time_seconds, peak_memory_mb, current_memory_mb)
    """
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Start memory tracking
        tracemalloc.start()

        # Measure execution time
        start_time = time.time()
        convert_instance(instance_path, temp_path, validate_filing_indicators=validate)
        end_time = time.time()

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        execution_time = end_time - start_time
        peak_memory_mb = peak / 1024 / 1024
        current_memory_mb = current / 1024 / 1024

        return execution_time, peak_memory_mb, current_memory_mb


def run_performance_tests():
    """Run performance tests and print results"""
    print("=" * 80)
    print("FILING INDICATOR VALIDATION - PERFORMANCE TEST")
    print("=" * 80)
    print()

    for test_file in TEST_FILES:
        if not test_file.exists():
            print(f"Skipping {test_file.name} (file not found)")
            continue

        print(f"\nTest File: {test_file.name}")
        print(f"File Size: {test_file.stat().st_size / 1024 / 1024:.2f} MB")
        print("-" * 80)

        # Run multiple iterations for more accurate timing
        iterations = 3

        # Test WITH validation
        print(f"\nWith Validation (averaging {iterations} runs):")
        times_with = []
        memory_with = []
        for i in range(iterations):
            exec_time, peak_mem, curr_mem = measure_performance(test_file, validate=True)
            times_with.append(exec_time)
            memory_with.append(peak_mem)
            print(f"  Run {i+1}: {exec_time:.3f}s, Peak Memory: {peak_mem:.2f} MB")

        avg_time_with = sum(times_with) / len(times_with)
        avg_mem_with = sum(memory_with) / len(memory_with)

        # Test WITHOUT validation
        print(f"\nWithout Validation (averaging {iterations} runs):")
        times_without = []
        memory_without = []
        for i in range(iterations):
            exec_time, peak_mem, curr_mem = measure_performance(test_file, validate=False)
            times_without.append(exec_time)
            memory_without.append(peak_mem)
            print(f"  Run {i+1}: {exec_time:.3f}s, Peak Memory: {peak_mem:.2f} MB")

        avg_time_without = sum(times_without) / len(times_without)
        avg_mem_without = sum(memory_without) / len(memory_without)

        # Calculate overhead
        time_overhead = ((avg_time_with - avg_time_without) / avg_time_without * 100) if avg_time_without > 0 else 0
        mem_overhead = ((avg_mem_with - avg_mem_without) / avg_mem_without * 100) if avg_mem_without > 0 else 0

        print("\n" + "=" * 80)
        print(f"SUMMARY FOR {test_file.name}")
        print("=" * 80)
        print(f"Average Time WITH validation:    {avg_time_with:.3f}s")
        print(f"Average Time WITHOUT validation: {avg_time_without:.3f}s")
        print(f"Time Overhead:                   {time_overhead:+.2f}%")
        print()
        print(f"Average Peak Memory WITH validation:    {avg_mem_with:.2f} MB")
        print(f"Average Peak Memory WITHOUT validation: {avg_mem_without:.2f} MB")
        print(f"Memory Overhead:                        {mem_overhead:+.2f}%")
        print("=" * 80)
        print()


if __name__ == "__main__":
    run_performance_tests()
