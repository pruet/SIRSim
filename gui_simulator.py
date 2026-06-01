#!/usr/bin/env python3
"""
SIR Network Epidemic Simulator GUI
Author: Antigravity
Version: 1.0.0 (based on Simulator Engine v2.15.0)

A premium, modern Tkinter-based desktop graphical interface for running,
evaluating, and comparing network-level epidemic containment strategies.
"""

import os
import sys
import queue
import threading
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv

# Import our simulator components
from sir_simulator import run_sir_simulation, SUPPRESSION_REGISTRY, parse_netlogo_world

class QueueWriteRedirector:
    """Redirects writes to a thread-safe Queue."""
    def __init__(self, q, log_type="stdout"):
        self.q = q
        self.log_type = log_type
        
    def write(self, string):
        if string.strip():
            self.q.put(("log", (self.log_type, string)))
            
    def flush(self):
        pass

class SirSimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SIR Network Epidemic Simulation Platform")
        self.root.geometry("1150x760")
        self.root.minsize(1050, 700)
        
        # Thread communication queue
        self.msg_queue = queue.Queue()
        
        # Keep track of active image reference to prevent garbage collection
        self.chart_image = None
        self.last_generated_plot = None
        
        # Initial parameters state
        self.selected_file_path = tk.StringVar()
        default_file = "vone_300_6_3.csv"
        if os.path.exists(default_file):
            self.selected_file_path.set(os.path.abspath(default_file))
            
        # Status message
        self.status_var = tk.StringVar(value="Ready")
        
        # Styling and Theme Configuration
        self.setup_styles()
        self.create_widgets()
        
        # Start thread-safe queue polling loop
        self.poll_queue()
        
        # Redirect stdout and stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = QueueWriteRedirector(self.msg_queue, "stdout")
        sys.stderr = QueueWriteRedirector(self.msg_queue, "stderr")
        
        self.log_to_console("system", "Simulator Engine v2.15.0 Loaded.\nGUI Interface Initialized successfully.")
        if self.selected_file_path.get():
            self.log_to_console("system", f"Default network graph loaded: {os.path.basename(self.selected_file_path.get())}")
            self.update_network_info()

    def setup_styles(self):
        """Sets up custom styles to give a modern, premium appearance."""
        self.style = ttk.Style()
        
        # Clean modern light theme background
        self.root.configure(bg="#f8fafc") # slate-50
        
        # Configure frames
        self.style.configure(".", background="#f8fafc", font=("Helvetica", 10))
        self.style.configure("Card.TFrame", background="#ffffff", relief="flat")
        self.style.configure("Header.TFrame", background="#0f172a") # slate-900
        
        # Configure Labels
        self.style.configure("HeaderTitle.TLabel", background="#0f172a", foreground="#ffffff", font=("Helvetica", 16, "bold"))
        self.style.configure("HeaderSub.TLabel", background="#0f172a", foreground="#94a3b8", font=("Helvetica", 10, "italic"))
        self.style.configure("Title.TLabel", font=("Helvetica", 12, "bold"), foreground="#0f172a", background="#ffffff")
        self.style.configure("TabLabel.TLabel", font=("Helvetica", 10, "bold"), foreground="#475569")
        
        # Configure Notebooks (Tabs)
        self.style.configure("TNotebook", background="#f8fafc", borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#e2e8f0", foreground="#475569", padding=[12, 5], font=("Helvetica", 9, "bold"))
        self.style.map("TNotebook.Tab",
            background=[("selected", "#ffffff"), ("active", "#cbd5e1")],
            foreground=[("selected", "#2563eb")] # Primary blue on selected
        )
        
        # Configure Buttons
        self.style.configure("Primary.TButton", font=("Helvetica", 10, "bold"), background="#2563eb", foreground="#ffffff")
        self.style.map("Primary.TButton",
            background=[("active", "#1d4ed8"), ("disabled", "#cbd5e1")]
        )
        self.style.configure("Secondary.TButton", font=("Helvetica", 9, "bold"), background="#e2e8f0", foreground="#334155")
        
        # LabelFrames
        self.style.configure("TLabelframe", background="#ffffff", relief="solid", borderwidth=1, bordercolor="#e2e8f0")
        self.style.configure("TLabelframe.Label", background="#ffffff", font=("Helvetica", 9, "bold"), foreground="#1e293b")
        
        # Scale (Slider) and Entry
        self.style.configure("Horizontal.TScale", background="#ffffff")
        self.style.configure("TCheckbutton", background="#ffffff", font=("Helvetica", 9))
        self.style.configure("TRadiobutton", background="#ffffff", font=("Helvetica", 9))

    def create_widgets(self):
        """Creates and layouts GUI components."""
        # Top Header Banner
        header = ttk.Frame(self.root, style="Header.TFrame", padding=[15, 12])
        header.pack(fill=tk.X, side=tk.TOP)
        
        lbl_title = ttk.Label(header, text="EPIDEMIC NETWORK SIMULATOR", style="HeaderTitle.TLabel")
        lbl_title.pack(anchor=tk.W)
        
        lbl_sub = ttk.Label(header, text="Engine Version: 2.15.0 | Robust Louvain Community Detection & Spectral Immunization Suppression", style="HeaderSub.TLabel")
        lbl_sub.pack(anchor=tk.W, pady=[2, 0])
        
        # Horizontal Split Panel
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        
        # Left Panel (Inputs Card)
        left_panel = ttk.Frame(paned, padding=[5, 5])
        paned.add(left_panel, weight=1)
        
        # Left Container Card
        left_card = ttk.Frame(left_panel, style="Card.TFrame", padding=15, relief="solid", borderwidth=1)
        left_card.pack(fill=tk.BOTH, expand=True)
        
        # Left Panel Title
        ttk.Label(left_card, text="Simulation Parameters", style="Title.TLabel").pack(anchor=tk.W, pady=[0, 10])
        
        # Tabs for Parameters Organization
        self.param_notebook = ttk.Notebook(left_card)
        self.param_notebook.pack(fill=tk.BOTH, expand=True)
        
        self.tab_network = ttk.Frame(self.param_notebook, style="Card.TFrame", padding=10)
        self.tab_strategies = ttk.Frame(self.param_notebook, style="Card.TFrame", padding=10)
        self.tab_execution = ttk.Frame(self.param_notebook, style="Card.TFrame", padding=10)
        
        self.param_notebook.add(self.tab_network, text="Network & Epidemic")
        self.param_notebook.add(self.tab_strategies, text="Suppression Strategies")
        self.param_notebook.add(self.tab_execution, text="Runs & Concurrency")
        
        # Populate Tabs
        self.build_tab_network()
        self.build_tab_strategies()
        self.build_tab_execution()
        
        # Right Panel (Output Cards)
        right_panel = ttk.Frame(paned, padding=[5, 5])
        paned.add(right_panel, weight=2)
        
        right_card = ttk.Frame(right_panel, style="Card.TFrame", padding=15, relief="solid", borderwidth=1)
        right_card.pack(fill=tk.BOTH, expand=True)
        
        # Tabs for Results Output
        self.result_notebook = ttk.Notebook(right_card)
        self.result_notebook.pack(fill=tk.BOTH, expand=True)
        
        self.tab_chart = ttk.Frame(self.result_notebook, style="Card.TFrame", padding=5)
        self.tab_metrics = ttk.Frame(self.result_notebook, style="Card.TFrame", padding=10)
        self.tab_console = ttk.Frame(self.result_notebook, style="Card.TFrame", padding=5)
        
        self.result_notebook.add(self.tab_chart, text="Infection Curves Plot")
        self.result_notebook.add(self.tab_metrics, text="Summary Statistics Table")
        self.result_notebook.add(self.tab_console, text="Execution Console Logs")
        
        # Populate Right Tabs
        self.build_tab_chart()
        self.build_tab_metrics()
        self.build_tab_console()
        
        # Bottom Bar Frame
        bottom_bar = ttk.Frame(self.root, style="Card.TFrame", padding=10, relief="solid", borderwidth=1)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=12, pady=[0, 10])
        
        # Status Indicator
        status_lbl_desc = ttk.Label(bottom_bar, text="Status: ", font=("Helvetica", 10, "bold"), background="#ffffff")
        status_lbl_desc.pack(side=tk.LEFT)
        status_lbl = ttk.Label(bottom_bar, textvariable=self.status_var, background="#ffffff", foreground="#475569")
        status_lbl.pack(side=tk.LEFT)
        
        # Action Buttons on Right
        self.btn_run = tk.Button(
            bottom_bar, text="Run Simulation", command=self.start_simulation_thread,
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", activeforeground="#ffffff",
            font=("Helvetica", 10, "bold"), relief="flat", padx=20, pady=6, cursor="hand2"
        )
        self.btn_run.pack(side=tk.RIGHT)
        
        # Network graph brief label in bottom bar
        self.lbl_graph_brief = ttk.Label(bottom_bar, text="No graph loaded", background="#ffffff", foreground="#64748b", font=("Helvetica", 9, "italic"))
        self.lbl_graph_brief.pack(side=tk.RIGHT, padx=20)

    # ==================== PARAMETER TABS BUILDERS ====================
    
    def build_tab_network(self):
        """Builds Network Loading and Basic Transmission Parameters Tab."""
        # File selector frame
        frame_file = ttk.LabelFrame(self.tab_network, text="1. Network Data Source", padding=8)
        frame_file.pack(fill=tk.X, pady=[0, 12])
        
        # Selected File Path Label
        lbl_file = ttk.Label(frame_file, textvariable=self.selected_file_path, font=("Courier", 8), foreground="#475569", background="#ffffff")
        lbl_file.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=[0, 8])
        
        btn_browse = ttk.Button(frame_file, text="Select Graph CSV", command=self.browse_file, style="Secondary.TButton")
        btn_browse.pack(side=tk.RIGHT)
        
        # Epidemic parameters frame
        frame_epidemic = ttk.LabelFrame(self.tab_network, text="2. Transmission & Disease Dynamics", padding=10)
        frame_epidemic.pack(fill=tk.BOTH, expand=True)
        
        # Override toggle
        self.override_disease = tk.BooleanVar(value=False)
        chk_override = ttk.Checkbutton(
            frame_epidemic, text="Override Network Default disease parameters",
            variable=self.override_disease, command=self.toggle_disease_fields
        )
        chk_override.pack(anchor=tk.W, pady=[0, 10])
        
        # Spread Chance
        lbl_s = ttk.Label(frame_epidemic, text="Spread Chance (%):", background="#ffffff")
        lbl_s.pack(anchor=tk.W)
        self.slider_s = ttk.Scale(frame_epidemic, from_=0, to=100, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.slider_s.set(10.0)
        self.slider_s.pack(fill=tk.X, pady=[0, 8])
        
        # Recovery Chance
        lbl_r = ttk.Label(frame_epidemic, text="Recovery Chance (%):", background="#ffffff")
        lbl_r.pack(anchor=tk.W)
        self.slider_r = ttk.Scale(frame_epidemic, from_=0, to=100, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.slider_r.set(5.0)
        self.slider_r.pack(fill=tk.X, pady=[0, 8])
        
        # Resistance Chance
        lbl_g = ttk.Label(frame_epidemic, text="Gain Resistance Chance (%):", background="#ffffff")
        lbl_g.pack(anchor=tk.W)
        self.slider_g = ttk.Scale(frame_epidemic, from_=0, to=100, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.slider_g.set(5.0)
        self.slider_g.pack(fill=tk.X, pady=[0, 8])
        
        # Virus Check Frequency
        lbl_f = ttk.Label(frame_epidemic, text="Virus Check Frequency (ticks):", background="#ffffff")
        lbl_f.pack(anchor=tk.W)
        self.spin_f = ttk.Spinbox(frame_epidemic, from_=1, to=50, width=5)
        self.spin_f.set(1)
        self.spin_f.pack(anchor=tk.W, pady=[0, 12])
        
        # Initial outbreak size frame
        frame_outbreak = ttk.LabelFrame(self.tab_network, text="3. Seed Outbreak Configuration", padding=8)
        frame_outbreak.pack(fill=tk.X, pady=[8, 0])
        
        self.override_outbreak = tk.BooleanVar(value=False)
        chk_outbreak = ttk.Checkbutton(
            frame_outbreak, text="Override Initial Infected Outbreak Size",
            variable=self.override_outbreak, command=self.toggle_outbreak_field
        )
        chk_outbreak.pack(anchor=tk.W, pady=[0, 5])
        
        self.spin_outbreak = ttk.Spinbox(frame_outbreak, from_=1, to=500, width=8)
        self.spin_outbreak.set(3)
        self.spin_outbreak.pack(anchor=tk.W)
        
        # Set initial interactive states
        self.toggle_disease_fields()
        self.toggle_outbreak_field()

    def build_tab_strategies(self):
        """Builds Strategy Selector and Suppression Parameters Tab."""
        # Strategies checklist
        frame_sel = ttk.LabelFrame(self.tab_strategies, text="1. Select Strategy to Evaluate", padding=10)
        frame_sel.pack(fill=tk.X, pady=[0, 12])
        
        ttk.Label(frame_sel, text="Strategy Algorithm:", background="#ffffff").pack(anchor=tk.W)
        
        # Strategy Combobox
        self.strategies_options = ["all", "baseline"] + list(SUPPRESSION_REGISTRY.keys())
        self.strategy_var = tk.StringVar(value="all")
        self.combo_strategy = ttk.Combobox(frame_sel, textvariable=self.strategy_var, values=self.strategies_options, state="readonly")
        self.combo_strategy.pack(fill=tk.X, pady=[4, 8])
        self.combo_strategy.bind("<<ComboboxSelected>>", self.on_strategy_selected)
        
        # Dynamic strategy note/explanation
        self.lbl_strategy_note = ttk.Label(frame_sel, text="", foreground="#4b5563", font=("Helvetica", 9, "italic"), wraplength=260, background="#ffffff")
        self.lbl_strategy_note.pack(fill=tk.X)
        
        # Suppression parameters
        self.frame_suppression = ttk.LabelFrame(self.tab_strategies, text="2. Strategy Parameters", padding=10)
        self.frame_suppression.pack(fill=tk.BOTH, expand=True)
        
        # Suppression Ratio (p)
        lbl_p_desc = ttk.Label(self.frame_suppression, text="Suppression Ratio (targeted nodes/edges fraction):", background="#ffffff")
        lbl_p_desc.pack(anchor=tk.W)
        
        self.override_ratio = tk.BooleanVar(value=False)
        self.chk_ratio = ttk.Checkbutton(
            self.frame_suppression, text="Override Ratio (default maps to vaccination fraction)",
            variable=self.override_ratio, command=self.toggle_ratio_field
        )
        self.chk_ratio.pack(anchor=tk.W, pady=[2, 4])
        
        self.slider_p = ttk.Scale(self.frame_suppression, from_=0.0, to=1.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.slider_p.set(0.10)
        self.slider_p.pack(fill=tk.X, pady=[0, 10])
        
        # Suppression Percentage (P)
        self.lbl_P = ttk.Label(self.frame_suppression, text="Suppression Intensity (edge weight reduction %):", background="#ffffff")
        self.lbl_P.pack(anchor=tk.W)
        self.slider_P = ttk.Scale(self.frame_suppression, from_=0, to=100, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.slider_P.set(90.0)
        self.slider_P.pack(fill=tk.X, pady=[0, 10])
        
        # Vaccination Fraction (v)
        self.lbl_v = ttk.Label(self.frame_suppression, text="Vaccination Fraction (nodes baseline immunization %):", background="#ffffff")
        self.lbl_v.pack(anchor=tk.W)
        self.slider_v = ttk.Scale(self.frame_suppression, from_=0.0, to=1.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.slider_v.set(0.10)
        self.slider_v.pack(fill=tk.X, pady=[0, 10])
        
        # Quarantine Chance (q)
        self.lbl_q = ttk.Label(self.frame_suppression, text="Quarantine Success Probability (per infected check):", background="#ffffff")
        self.lbl_q.pack(anchor=tk.W)
        self.slider_q = ttk.Scale(self.frame_suppression, from_=0.0, to=1.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.slider_q.set(0.80)
        self.slider_q.pack(fill=tk.X)
        
        self.toggle_ratio_field()
        self.on_strategy_selected() # Trigger init explanation after all widgets are defined

    def build_tab_execution(self):
        """Builds Ticks, Runs, Time Alignment and Concurrency controls Tab."""
        # Monte Carlo Configuration Frame
        frame_mc = ttk.LabelFrame(self.tab_execution, text="1. Simulation Scale", padding=10)
        frame_mc.pack(fill=tk.X, pady=[0, 12])
        
        # Max Steps (t)
        ttk.Label(frame_mc, text="Max Ticks (Simulation steps):", background="#ffffff").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.spin_steps = ttk.Spinbox(frame_mc, from_=10, to=2000, width=8)
        self.spin_steps.set(500)
        self.spin_steps.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        # MC Runs (n)
        ttk.Label(frame_mc, text="Monte Carlo independent runs:", background="#ffffff").grid(row=1, column=0, sticky=tk.W, pady=6)
        self.spin_runs = ttk.Spinbox(frame_mc, from_=1, to=500, width=8)
        self.spin_runs.set(50)
        self.spin_runs.grid(row=1, column=1, sticky=tk.W, padx=10)
        
        # Alignment (a)
        ttk.Label(frame_mc, text="Time Alignment Averaging:", background="#ffffff").grid(row=2, column=0, sticky=tk.W, pady=6)
        self.align_var = tk.StringVar(value="align")
        frame_align_opts = ttk.Frame(frame_mc, style="Card.TFrame")
        frame_align_opts.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=8)
        ttk.Radiobutton(frame_align_opts, text="Time-Align (pad)", variable=self.align_var, value="align").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(frame_align_opts, text="Truncate at death", variable=self.align_var, value="truncate").pack(side=tk.LEFT, padx=5)
        
        # Concurrency & Process Limits Frame
        frame_parallel = ttk.LabelFrame(self.tab_execution, text="2. Multi-Core Concurrency Control", padding=10)
        frame_parallel.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame_parallel, text="Maximize multi-run throughput using ProcessPoolExecutor.", background="#ffffff", font=("Helvetica", 9, "italic"), foreground="#475569").pack(anchor=tk.W, pady=[0, 8])
        
        self.parallel_var = tk.BooleanVar(value=True)
        chk_parallel = ttk.Checkbutton(
            frame_parallel, text="Enable Multi-Process Parallel Execution",
            variable=self.parallel_var, command=self.toggle_parallel_fields
        )
        chk_parallel.pack(anchor=tk.W, pady=[0, 10])
        
        self.frame_workers_sub = ttk.Frame(frame_parallel, style="Card.TFrame", padding=[15, 0])
        self.frame_workers_sub.pack(fill=tk.X)
        
        self.worker_limit_var = tk.BooleanVar(value=False)
        self.chk_worker_limit = ttk.Checkbutton(
            self.frame_workers_sub, text="Limit concurrent workers / CPU cores",
            variable=self.worker_limit_var, command=self.toggle_worker_spin
        )
        self.chk_worker_limit.pack(anchor=tk.W, pady=[0, 5])
        
        self.frame_spin_workers = ttk.Frame(self.frame_workers_sub, style="Card.TFrame")
        self.frame_spin_workers.pack(anchor=tk.W)
        self.lbl_workers_count = ttk.Label(self.frame_spin_workers, text="Maximum Worker Processes:", background="#ffffff")
        self.lbl_workers_count.pack(side=tk.LEFT, padx=[10, 5])
        
        # Default to 4 workers limit
        self.spin_workers = ttk.Spinbox(self.frame_spin_workers, from_=2, to=64, width=5)
        self.spin_workers.set(4)
        self.spin_workers.pack(side=tk.LEFT)
        
        self.toggle_parallel_fields()

    # ==================== OUTPUT TABS BUILDERS ====================
    
    def build_tab_chart(self):
        """Builds Dynamic Plot Visualizer Tab."""
        # Scrollable container or canvas for chart image
        self.canvas_chart = tk.Canvas(self.tab_chart, bg="#f8fafc", highlightthickness=0)
        self.canvas_chart.pack(fill=tk.BOTH, expand=True)
        
        # Frame inside canvas to center the image
        self.lbl_chart_img = tk.Label(self.canvas_chart, text="No curves generated yet.\nConfigure parameters and click 'Run Simulation' below.", font=("Helvetica", 11, "italic"), bg="#f8fafc", fg="#64748b")
        self.lbl_chart_img.pack(fill=tk.BOTH, expand=True)

    def build_tab_metrics(self):
        """Builds Statistics Table Tab."""
        ttk.Label(self.tab_metrics, text="Evaluation metrics from strategy runs:", background="#ffffff", font=("Helvetica", 10, "bold"), foreground="#0f172a").pack(anchor=tk.W, pady=[0, 8])
        
        # Treeview Scrollbar
        scroll_y = ttk.Scrollbar(self.tab_metrics, orient=tk.VERTICAL)
        scroll_x = ttk.Scrollbar(self.tab_metrics, orient=tk.HORIZONTAL)
        
        # Treeview Grid
        cols = ("strategy", "peak_inf_qty", "peak_inf_pct", "peak_tick", "final_susc_pct", "duration", "exec_time")
        self.tree_metrics = ttk.Treeview(
            self.tab_metrics, columns=cols, show="headings",
            yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set
        )
        
        scroll_y.config(command=self.tree_metrics.yview)
        scroll_x.config(command=self.tree_metrics.xview)
        
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree_metrics.pack(fill=tk.BOTH, expand=True)
        
        # Define Columns Header & Widths
        self.tree_metrics.heading("strategy", text="Strategy Evaluated")
        self.tree_metrics.heading("peak_inf_qty", text="Peak Infected (Qty)")
        self.tree_metrics.heading("peak_inf_pct", text="Peak Infected (%)")
        self.tree_metrics.heading("peak_tick", text="Peak Tick")
        self.tree_metrics.heading("final_susc_pct", text="Final Susc. (%)")
        self.tree_metrics.heading("duration", text="Duration (Steps)")
        self.tree_metrics.heading("exec_time", text="Exec. Time (s)")
        
        self.tree_metrics.column("strategy", width=220, anchor=tk.W)
        self.tree_metrics.column("peak_inf_qty", width=120, anchor=tk.CENTER)
        self.tree_metrics.column("peak_inf_pct", width=120, anchor=tk.CENTER)
        self.tree_metrics.column("peak_tick", width=80, anchor=tk.CENTER)
        self.tree_metrics.column("final_susc_pct", width=120, anchor=tk.CENTER)
        self.tree_metrics.column("duration", width=110, anchor=tk.CENTER)
        self.tree_metrics.column("exec_time", width=100, anchor=tk.CENTER)
        
        # Action button to clear table
        btn_clear = ttk.Button(self.tab_metrics, text="Clear Metrics Table", command=self.clear_metrics_table, style="Secondary.TButton")
        btn_clear.pack(anchor=tk.E, pady=[8, 0])

    def build_tab_console(self):
        """Builds Live Monospaced Output Logs Console Tab."""
        frame_top = ttk.Frame(self.tab_console, style="Card.TFrame")
        frame_top.pack(fill=tk.X, pady=[2, 4])
        ttk.Label(frame_top, text="Live Simulator Standard Output Console:", background="#ffffff", font=("Helvetica", 9, "bold")).pack(side=tk.LEFT)
        
        btn_clear_log = ttk.Button(frame_top, text="Clear Logs", command=self.clear_console, style="Secondary.TButton")
        btn_clear_log.pack(side=tk.RIGHT)
        
        # Console monospaced scrollable text widget
        scroll = ttk.Scrollbar(self.tab_console, orient=tk.VERTICAL)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.console_text = tk.Text(
            self.tab_console, wrap=tk.WORD, font=("Courier", 9),
            bg="#0f172a", fg="#f8fafc", # Dark terminal colors
            insertbackground="#ffffff", yscrollcommand=scroll.set,
            state="disabled", borderwidth=0
        )
        self.console_text.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.console_text.yview)
        
        # Set text tags for coloring log levels
        self.console_text.tag_config("stdout", foreground="#f8fafc")
        self.console_text.tag_config("stderr", foreground="#f87171") # Soft red for error
        self.console_text.tag_config("system", foreground="#60a5fa") # Soft blue for system info
        self.console_text.tag_config("success", foreground="#34d399") # Soft green for success info

    # ==================== INTERACTIVE TOGGLES ====================
    
    def browse_file(self):
        """Launches file selector to choose a NetLogo CSV graph file."""
        initial_dir = os.path.dirname(self.selected_file_path.get()) if self.selected_file_path.get() else os.getcwd()
        path = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Select NetLogo export-world CSV Graph",
            filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*"))
        )
        if path:
            self.selected_file_path.set(os.path.abspath(path))
            self.log_to_console("system", f"\nSelected network graph: {os.path.basename(path)}")
            self.update_network_info()
            
    def update_network_info(self):
        """Reads NetLogo graph file to display basic stats in bottom bar."""
        path = self.selected_file_path.get()
        if not path or not os.path.exists(path):
            self.lbl_graph_brief.config(text="No graph loaded")
            return
            
        try:
            globals_dict, nodes, adj = parse_netlogo_world(path)
            num_nodes = len(nodes)
            num_edges = sum(len(neighbors) for neighbors in adj.values()) // 2
            brief = f"Network: {os.path.basename(path)} ({num_nodes} nodes, {num_edges} edges)"
            self.lbl_graph_brief.config(text=brief)
        except Exception as e:
            self.lbl_graph_brief.config(text="Error parsing graph CSV")
            self.log_to_console("stderr", f"Error pre-parsing graph CSV: {e}")
            
    def toggle_disease_fields(self):
        """Enables/Disables disease sliders based on checkbox state."""
        state = "normal" if self.override_disease.get() else "disabled"
        self.slider_s.config(state=state)
        self.slider_r.config(state=state)
        self.slider_g.config(state=state)
        self.spin_f.config(state=state)
        
    def toggle_outbreak_field(self):
        """Enables/Disables outbreak override spinbox."""
        state = "normal" if self.override_outbreak.get() else "disabled"
        self.spin_outbreak.config(state=state)
        
    def toggle_ratio_field(self):
        """Enables/Disables suppression ratio slider."""
        state = "normal" if self.override_ratio.get() else "disabled"
        self.slider_p.config(state=state)
        
    def toggle_parallel_fields(self):
        """Enables/Disables multi-process related options based on checkbox state."""
        state = "normal" if self.parallel_var.get() else "disabled"
        self.chk_worker_limit.config(state=state)
        self.toggle_worker_spin()
        
    def toggle_worker_spin(self):
        """Enables/Disables max worker spinbox."""
        if self.parallel_var.get() and self.worker_limit_var.get():
            self.lbl_workers_count.config(state="normal")
            self.spin_workers.config(state="normal")
        else:
            self.lbl_workers_count.config(state="disabled")
            self.spin_workers.config(state="disabled")
            
    def on_strategy_selected(self, event=None):
        """Disables/Enables strategy parameters based on selected algorithm."""
        strat = self.strategy_var.get()
        
        # Update strategy explanation notes
        explanations = {
            "all": "Evaluates all suppression strategies sequentially along with baseline unsuppressed propagation, rendering a comparative curve chart.",
            "baseline": "Simulates natural epidemic propagation without any network suppression applied. Useful as an unsuppressed control benchmark.",
            "netshield_edge_suppression": "Spectral edge suppression algorithm. Maximizes network-level Shield-value strictly over susceptible nodes, and suppresses adjacent edges incident to central nodes.",
            "centrality_edge_suppression": "Eigenvector centrality-based edge suppression. Targets highly central bridging nodes, and suppresses transmission rates of adjacent connections.",
            "greedy_edge_weight_suppression": "Link-level containment. Globally sorts all transmission links in descending order of weight, and suppresses the highest-probability links first.",
            "reliable_cluster_edge_suppression": "Community-level containment based on Boonma's paper. Detects robust clusters using Louvain partitioning, and suppresses bridging links to isolate clusters."
        }
        
        self.lbl_strategy_note.config(text=explanations.get(strat, ""))
        
        # Configure field visibilities based on strategy applicability
        if strat == "baseline":
            # Baseline doesn't use suppression parameters
            self.set_suppression_fields_state("disabled")
            self.lbl_strategy_note.config(foreground="#dc2626") # Alert color for baseline warning
        else:
            self.set_suppression_fields_state("normal")
            self.lbl_strategy_note.config(foreground="#4b5563")
            
    def set_suppression_fields_state(self, state):
        """Helper to enable/disable suppression tab parameters."""
        self.chk_ratio.config(state=state)
        self.slider_p.config(state=state if self.override_ratio.get() else "disabled")
        self.slider_P.config(state=state)
        self.slider_v.config(state=state)
        self.slider_q.config(state=state)
        self.lbl_P.config(state=state)
        self.lbl_v.config(state=state)
        self.lbl_q.config(state=state)

    # ==================== SYSTEM THREADING & QUEUE ====================
    
    def log_to_console(self, log_type, message):
        """Puts log message safely onto thread-safe queue."""
        self.msg_queue.put(("log", (log_type, message + "\n")))

    def poll_queue(self):
        """Regularly checks the thread-safe Queue to update UI in main thread."""
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                msg_type = msg[0]
                
                if msg_type == "log":
                    log_type, text = msg[1]
                    self.append_log(log_type, text)
                elif msg_type == "status":
                    self.status_var.set(msg[1])
                elif msg_type == "complete":
                    self.on_simulation_complete(msg[1])
                elif msg_type == "error":
                    self.on_simulation_error(msg[1])
        except queue.Empty:
            pass
            
        # Poll every 100 milliseconds
        self.root.after(100, self.poll_queue)

    def append_log(self, log_type, text):
        """Appends formatted text safely to console Text widget."""
        self.console_text.config(state="normal")
        self.console_text.insert(tk.END, text, log_type)
        self.console_text.see(tk.END)
        self.console_text.config(state="disabled")

    def clear_console(self):
        """Clears console text."""
        self.console_text.config(state="normal")
        self.console_text.delete("1.0", tk.END)
        self.console_text.config(state="disabled")
        
    def clear_metrics_table(self):
        """Clears metrics Treeview table."""
        for item in self.tree_metrics.get_children():
            self.tree_metrics.delete(item)

    # ==================== CORE SIMULATOR EXECUTION ====================
    
    def start_simulation_thread(self):
        """Starts heavy Monte Carlo simulation runs in a background thread."""
        # Validation checks
        file_path = self.selected_file_path.get()
        if not file_path:
            messagebox.showerror("Error", "Please select a NetLogo world CSV file first.")
            return
            
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"Graph file '{os.path.basename(file_path)}' does not exist.")
            return
            
        # Disable Run Button to prevent multiple threads thrashed
        self.btn_run.config(state=tk.DISABLED, text="Running...")
        self.status_var.set("Initializing Monte Carlo simulation thread...")
        self.result_notebook.select(self.tab_console) # Bring log console to front
        self.clear_console()
        
        # Resolve variables from GUI widgets
        runs = int(self.spin_runs.get())
        steps = int(self.spin_steps.get())
        alignment = self.align_var.get()
        strategy_name = self.strategy_var.get()
        
        # Dynamic overrides
        spread = float(self.slider_s.get()) if self.override_disease.get() else None
        recovery = float(self.slider_r.get()) if self.override_disease.get() else None
        resistance = float(self.slider_g.get()) if self.override_disease.get() else None
        frequency = int(self.spin_f.get()) if self.override_disease.get() else None
        
        outbreak = int(self.spin_outbreak.get()) if self.override_outbreak.get() else None
        
        supp_ratio = float(self.slider_p.get()) if self.override_ratio.get() else None
        supp_pct = float(self.slider_P.get())
        vacc_fraction = float(self.slider_v.get())
        quar_chance = float(self.slider_q.get())
        
        # Concurrency/Process Limit
        if self.parallel_var.get():
            if self.worker_limit_var.get():
                workers = int(self.spin_workers.get())
            else:
                workers = "all"
        else:
            workers = None
            
        # Pack everything into dictionary for thread
        sim_kwargs = {
            "file_path": file_path,
            "runs": runs,
            "steps": steps,
            "alignment": alignment,
            "strategy_name": strategy_name,
            "suppression_ratio": supp_ratio,
            "suppression_percentage": supp_pct,
            "spread_chance": spread,
            "recovery_chance": recovery,
            "resistance_chance": resistance,
            "virus_check_frequency": frequency,
            "vaccination_fraction": vacc_fraction,
            "quarantine_chance": quar_chance,
            "initial_outbreak_size": outbreak,
            "workers": workers
        }
        
        # Launch background Thread
        thread = threading.Thread(target=self.run_heavy_simulation, args=(sim_kwargs,), daemon=True)
        thread.start()

    def run_heavy_simulation(self, kwargs):
        """Runs the simulation engine safely inside thread."""
        try:
            self.msg_queue.put(("status", "Running Monte Carlo simulations in background..."))
            self.log_to_console("system", f"=== STARTING MONTE CARLO SIMULATION ===")
            self.log_to_console("system", f"Strategies requested: '{kwargs['strategy_name']}'")
            self.log_to_console("system", f"Independent runs: {kwargs['runs']} | Max ticks: {kwargs['steps']}")
            self.log_to_console("system", f"Parallel execution: {'Enabled (workers=' + str(kwargs['workers']) + ')' if kwargs['workers'] is not None else 'Disabled (Sequential)'}")
            self.log_to_console("system", f"--------------------------------------------------")
            
            # If strategy is "all", we must loop through them manually in the GUI to tabulate all metrics
            selected_strategy = kwargs["strategy_name"]
            
            all_avg_histories = {}
            summary_data = []
            
            # Resolve strategies to run
            available_strategies = ["baseline"] + list(SUPPRESSION_REGISTRY.keys())
            if selected_strategy == "all":
                run_list = available_strategies
            else:
                run_list = [selected_strategy]
                
            for strategy in run_list:
                self.log_to_console("system", f"\n[Run] Evaluating strategy: '{strategy}'...")
                self.msg_queue.put(("status", f"Evaluating strategy: '{strategy}'..."))
                
                # Copy arguments and override current strategy
                run_kwargs = kwargs.copy()
                run_kwargs["strategy_name"] = strategy
                
                # Run the simulator engine! (stdout is automatically intercepted by our redirector class)
                avg_hist, summary = run_sir_simulation(**run_kwargs)
                
                all_avg_histories[strategy] = avg_hist
                summary_data.append(summary)
                
            # Pack results to send to main thread
            results = {
                "selected_strategy": selected_strategy,
                "summary_data": summary_data,
                "all_avg_histories": all_avg_histories,
                "kwargs": kwargs
            }
            
            self.msg_queue.put(("complete", results))
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.msg_queue.put(("error", (str(e), tb)))

    def on_simulation_complete(self, results):
        """Processes results in main thread upon thread execution completion."""
        self.btn_run.config(state=tk.NORMAL, text="Run Simulation")
        self.status_var.set("Simulation Complete!")
        self.log_to_console("success", "\n=== MONTE CARLO SIMULATION COMPLETED SUCCESSFULLY ===")
        
        summary_data = results["summary_data"]
        all_avg_histories = results["all_avg_histories"]
        selected_strategy = results["selected_strategy"]
        kwargs = results["kwargs"]
        
        # 1. Update treeview metrics table
        # We don't clear old rows so users can compare multiple custom runs if they want!
        # Instead, we just insert the new metrics
        for row in summary_data:
            name_str = row['strategy'].replace('_', ' ').title()
            self.tree_metrics.insert(
                "", tk.END,
                values=(
                    name_str,
                    f"{row['peak_infected']:.2f}",
                    f"{row['peak_infected_pct']:.2f}%",
                    row['peak_tick'],
                    f"{row['final_susceptible_pct']:.2f}%",
                    row['duration'],
                    f"{row['execution_time']:.4f}s"
                )
            )
            
        # 2. Look for the dynamically generated parameters-reflecting PNG chart
        # Resolving parameters for finding files
        globals_dict, nodes, adj = parse_netlogo_world(kwargs["file_path"])
        
        fallback_spread = 10.0
        fallback_recovery = 5.0
        
        spread_val = kwargs["spread_chance"] if kwargs["spread_chance"] is not None else (
            float(globals_dict.get('virus-spread-chance')) if globals_dict.get('virus-spread-chance') is not None else fallback_spread
        )
        recovery_val = kwargs["recovery_chance"] if kwargs["recovery_chance"] is not None else (
            float(globals_dict.get('recovery-chance')) if globals_dict.get('recovery-chance') is not None else fallback_recovery
        )
        supp_ratio_val = kwargs["suppression_ratio"] if kwargs["suppression_ratio"] is not None else kwargs["vaccination_fraction"]
        
        def fmt_num(val):
            if val is None:
                return "None"
            if isinstance(val, float) and val.is_integer():
                return str(int(val))
            return str(val)
            
        param_suffix = f"s{fmt_num(spread_val)}_r{fmt_num(recovery_val)}_p{fmt_num(supp_ratio_val)}_P{fmt_num(kwargs['suppression_percentage'])}_v{fmt_num(kwargs['vaccination_fraction'])}_q{fmt_num(kwargs['quarantine_chance'])}"
        
        # Decide base filename
        if selected_strategy == "all":
            base_name = "sir_comparison_curves.png"
        else:
            base_name = "sir_simulation_curves.png"
            
        # Dynamic filename
        root_base, ext = os.path.splitext(base_name)
        plot_filename = f"{root_base}_{param_suffix}{ext}"
        plot_path = os.path.abspath(plot_filename)
        
        self.log_to_console("system", f"Locating dynamically generated curves plot: {plot_filename}")
        
        if os.path.exists(plot_path):
            self.display_chart(plot_path)
            self.result_notebook.select(self.tab_chart) # Auto-switch to visual chart tab
        else:
            self.log_to_console("stderr", f"Could not find curves chart file at path: {plot_path}")
            messagebox.showwarning("Warning", f"Simulation completed successfully, but curve chart was not found at:\n{plot_path}")

    def on_simulation_error(self, err_info):
        """Processes exceptions caught in the simulation thread."""
        err_msg, tb_text = err_info
        self.btn_run.config(state=tk.NORMAL, text="Run Simulation")
        self.status_var.set("Simulation Failed!")
        
        # Log standard stack trace in Red inside terminal console
        self.log_to_console("stderr", f"\n=== THREAD CRASH LOGS ===")
        self.append_log("stderr", tb_text)
        
        messagebox.showerror("Simulation Crash", f"An error occurred in the simulation execution:\n\n{err_msg}\n\nSee full traceback in the console tab.")

    # ==================== GRAPHICS DISPLAY HELPER ====================
    
    def display_chart(self, plot_path):
        """Loads and embeds generated PNG chart in UI dynamically."""
        try:
            # Standard PhotoImage requires active garbage collection reference
            img = tk.PhotoImage(file=plot_path)
            
            # Clear blank state labels
            self.lbl_chart_img.config(image=img, text="")
            self.chart_image = img # Cache reference
            self.last_generated_plot = plot_path
            
            self.log_to_console("success", f"Embedded curve chart successfully in GUI: {os.path.basename(plot_path)}")
        except Exception as e:
            self.log_to_console("stderr", f"Error embedding chart in Canvas: {e}")

    def restore_system_handles(self):
        """Restores original system stdout and stderr handles on close."""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

def main():
    root = tk.Tk()
    app = SirSimulatorGUI(root)
    
    # Custom closing event to restore handles safely
    def on_closing():
        app.restore_system_handles()
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
