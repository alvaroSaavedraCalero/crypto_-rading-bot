#!/usr/bin/env python3
"""
Batch runner for all strategy optimizers with 1m timeframe.
This script runs each optimizer sequentially to avoid overwhelming system resources.
"""

import subprocess
import sys
from pathlib import Path

# List of all optimizer scripts
OPTIMIZERS = [
    "optimization/optimize_bollinger.py",
    "optimization/optimize_ict.py",
    "optimization/optimize_keltner.py",
    "optimization/optimize_macd_adx.py",
    "optimization/optimize_ma_rsi.py",
    "optimization/optimize_smart_money.py",
    "optimization/optimize_squeeze.py",
    "optimization/optimize_supertrend.py",
]

def run_optimizer(script_path: str) -> bool:
    """
    Run a single optimizer script.
    Returns True if successful, False otherwise.
    """
    print(f"\n{'='*80}")
    print(f"Running: {script_path}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=False,  # Show output in real-time
            text=True
        )
        print(f"\n✓ {script_path} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {script_path} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"\n✗ {script_path} failed with error: {e}")
        return False

def main():
    print("="*80)
    print("BATCH OPTIMIZER RUNNER - 1m Timeframe")
    print("="*80)
    print(f"\nTotal optimizers to run: {len(OPTIMIZERS)}")
    print("\nNOTE: Each optimizer is currently configured with its own symbol/timeframe.")
    print("You may need to manually edit each optimizer file to change to 1m timeframe.")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    
    results = {}
    
    for optimizer in OPTIMIZERS:
        success = run_optimizer(optimizer)
        results[optimizer] = "✓" if success else "✗"
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    for optimizer, status in results.items():
        print(f"{status} {optimizer}")
    
    successful = sum(1 for s in results.values() if s == "✓")
    print(f"\nCompleted: {successful}/{len(OPTIMIZERS)} optimizers")

if __name__ == "__main__":
    main()
