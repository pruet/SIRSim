# SIR Simulator CLI Parameters

This reference document contains the complete and consolidated list of all command-line parameters for the `sir_simulator.py` (v2.14.0) network epidemic simulator.

## Parameter Reference Table

| Flag (Short/Long) | Name | Type | Default / Fallback | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`-s` / `--spread-chance`** | Spread Chance | `float` | CSV Globals (`10.0`) | Probability of infection transmission per step across a connected link (expressed in range 0 to 100). |
| **`-r` / `--recovery-chance`** | Recovery Chance | `float` | CSV Globals (`5.0`) | Probability of an infected node recovering per step (expressed in range 0 to 100). |
| **`-g` / `--resistance-chance`** | Resistance Chance | `float` | CSV Globals (`5.0`) | Probability that a recovering node gains permanent immunity (resistance) instead of returning to a susceptible state. |
| **`-f` / `--virus-check-frequency`**| Check Frequency | `int` | CSV Globals (`1`) | Check interval (in ticks) at which infected nodes perform quarantine self-checks. |
| **`-i` / `--initial-outbreak-size`**| Outbreak Size | `int` | CSV Globals (`3`) | Override for the initial number of infected seed nodes at setup. |
| **`-t` / `--steps`** | Max Ticks | `int` | `500` | Maximum limit of time steps (ticks) to run the simulation. |
| **`-n` / `--runs`** | MC Runs | `int` | `50` | Number of independent Monte Carlo simulation runs to average for statistical aggregation. |
| **`-S` / `--strategies`** | Strategies | `list` | `all` | Strategies to evaluate (`baseline`, `netshield_edge_suppression`, `centrality_edge_suppression`, `greedy_edge_weight_suppression`, `reliable_cluster_edge_suppression`). |
| **`-p` / `--suppression-ratio`** | Supp. Ratio | `float` | Mapped to `-v` (`0.10`) | Fraction of nodes or edges targeted for suppression (ranges from `0.0` to `1.0`). |
| **`-P` / `--suppression-percentage`**| Supp. Weight % | `float` | `90.0` | Percentage reduction applied to the transmission probability of suppressed edges (0.0 to 100.0). |
| **`-v` / `--vaccination-fraction`** | Vacc. Fraction | `float` | `0.10` | Default suppression fraction used when `--suppression-ratio` is not explicitly set (0.0 to 1.0). |
| **`-q` / `--quarantine-chance`** | Quar. Chance | `float` | `0.80` | Probability of successfully isolating an infected node per step in infected quarantine strategies. |
| **`-j` / `--parallel`** | Parallel workers | `int/str`| `None` (Sequential) | Enables process-based parallel execution of Monte Carlo runs. Use `-j` for all cores, or `-j <N>` to limit concurrency to exactly $N$ processes. |
| **`-a` / `--alignment`** | Time Align | `str` | `align` | Time alignment mode for multi-run averaging: `'align'` (pads shorter runs with final state) or `'truncate'`. |
| **`-o` / `--output-plot`** | Curve Chart PNG | `str` | Param-suffixed PNG | Path to save curves chart (dynamically suffixed with active parameters). |
| **`-c` / `--output-csv`** | Summary CSV | `str` | `None` (Disabled) | File path where the evaluation summary metrics CSV will be saved (dynamically suffixed with active parameters). |

## Usage Examples

### 1. Basic Sequential Comparison
Run comparative simulations for all strategies with default parameters:
```bash
python sir_simulator.py vone_300_6_3.csv
```

### 2. Multi-Core Execution with Output CSV
Run simulation in parallel across all CPU cores and save results to a parameter-named CSV and PNG:
```bash
python sir_simulator.py vone_300_6_3.csv -j -c comparison_summary.csv
```

### 3. Capped Worker Process Limit
Evaluate a specific strategy using exactly 4 concurrent worker processes:
```bash
python sir_simulator.py vone_300_6_3.csv -S netshield_edge_suppression -j 4
```

### 4. Custom Parameters with Suffix Outputs
Run with customized transmission parameters, outputting to `comparison_summary_s10_r5_p0.05_P5_v0_q0.csv` and `sir_comparison_curves_s10_r5_p0.05_P5_v0_q0.png`:
```bash
python sir_simulator.py vone_300_6_3.csv -n 50 -s 10 -r 5 -p 0.05 -P 5 -v 0 -q 0 -c comparison_summary.csv
```
