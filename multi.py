#!/usr/bin/env python3
import sys
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.ticker import ScalarFormatter
import argparse

def process_rtt_csv(csv_file):
    """Process the RTT CSV file from tcpdump/tshark."""
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Check if we have the expected columns
        if 'frame.time_relative' in df.columns and 'tcp.analysis.ack_rtt' in df.columns:
            # Clean up data - ensure numeric types
            df['frame.time_relative'] = pd.to_numeric(df['frame.time_relative'], errors='coerce')
            df['tcp.analysis.ack_rtt'] = pd.to_numeric(df['tcp.analysis.ack_rtt'], errors='coerce')
        else:
            # Try with default column names (no headers)
            df.columns = ['time', 'tcp.seq', 'rtt'] if len(df.columns) == 3 else ['time', 'rtt']
            df['time'] = pd.to_numeric(df['time'], errors='coerce')
            df['rtt'] = pd.to_numeric(df['rtt'], errors='coerce')
            # Rename to standard names
            df = df.rename(columns={'time': 'frame.time_relative', 'rtt': 'tcp.analysis.ack_rtt'})
        
        # Drop rows with NaN values
        df = df.dropna(subset=['frame.time_relative', 'tcp.analysis.ack_rtt'])
        
        return df
    except Exception as e:
        print(f"Error processing RTT CSV file {csv_file}: {e}")
        return None

def process_iperf_json(json_file):
    """Process the iperf3 JSON file."""
    if not json_file or not os.path.exists(json_file):
        return None
    
    try:
        # Read the JSON file
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Extract intervals data
        intervals = data.get('intervals', [])
        
        # Create lists for time and throughput
        times = []
        throughput_values = []
        
        for interval in intervals:
            # Get the end time and throughput from each interval
            end_time = interval['sum']['end']
            bits_per_second = interval['sum']['bits_per_second']
            
            times.append(end_time)
            # Convert to Mbps for readability
            throughput_values.append(bits_per_second / 1e6)
        
        return {
            'times': times,
            'throughput': throughput_values
        }
    except Exception as e:
        print(f"Warning: Could not process iperf3 JSON file {json_file}: {e}")
        return None

def create_overlay_plot(rtt_data_list, iperf_data_list, labels, output_file=None):
    """Create a time series plot overlaying multiple RTT datasets."""
    fig, ax1 = plt.subplots(figsize=(14, 8))
    
    # Colors for different datasets - USE THESE INSTEAD
    colors = ['blue', 'red', 'green']
    styles = ['-', '--', '-.']
    
    # Plot each RTT dataset - FIX THIS PART
    for i, (rtt_data, label) in enumerate(zip(rtt_data_list, labels)):
        if rtt_data is not None:
            # Specify color and linestyle separately instead of as a format string
            ax1.plot(rtt_data['frame.time_relative'], rtt_data['tcp.analysis.ack_rtt'], 
                    color=colors[i], linestyle=styles[i], linewidth=1.2, alpha=0.7, 
                    label=f'RTT - {label}')
    
    ax1.set_xlabel('Time (seconds)', fontsize=12)
    ax1.set_ylabel('Round Trip Time (ms)', fontsize=12)
    
    # Add vertical lines for bandwidth changes
    markers = [5, 10, 15, 20]  # Change based on your test intervals
    marker_labels = ['5Mbps→2Mbps', '2Mbps→1Mbps', '1Mbps→500kbps', 'End of test']
    marker_colors = ['gray', 'gray', 'gray', 'gray']
    
    for marker, label, color in zip(markers, marker_labels, marker_colors):
        ax1.axvline(x=marker, color=color, linestyle='--', alpha=0.5, label=label)
    
    # Handle iperf data if available - FIX THIS PART TOO
    ax2 = None
    if any(iperf_data is not None for iperf_data in iperf_data_list):
        ax2 = ax1.twinx()
        for i, (iperf_data, label) in enumerate(zip(iperf_data_list, labels)):
            if iperf_data is not None:
                # Specify color and linestyle separately here too
                ax2.plot(iperf_data['times'], iperf_data['throughput'], 
                         color=colors[i], linestyle='-', linewidth=1.0, alpha=0.4, 
                         label=f'Throughput - {label}')
        ax2.set_ylabel('Throughput (Mbps)', fontsize=12)
    
    # Add statistics text for each dataset
    y_pos = 0.02
    for i, (rtt_data, label) in enumerate(zip(rtt_data_list, labels)):
        if rtt_data is not None:
            stats_text = f"{label} Stats:\n"
            stats_text += f"Avg RTT: {rtt_data['tcp.analysis.ack_rtt'].mean():.2f} ms\n"
            stats_text += f"Min RTT: {rtt_data['tcp.analysis.ack_rtt'].min():.2f} ms\n"
            stats_text += f"Max RTT: {rtt_data['tcp.analysis.ack_rtt'].max():.2f} ms\n"
            stats_text += f"Std Dev: {rtt_data['tcp.analysis.ack_rtt'].std():.2f} ms"
            
            plt.figtext(0.02, y_pos, stats_text, fontsize=9, 
                        bbox=dict(facecolor=colors[i], alpha=0.1))
            y_pos += 0.15
    
    # Create a combined legend
    handles1, labels1 = ax1.get_legend_handles_labels()
    if ax2:
        handles2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(handles1 + handles2, labels1 + labels2, loc='upper right', 
                  fontsize=9, framealpha=0.7)
    else:
        ax1.legend(loc='upper right', fontsize=9, framealpha=0.7)
    
    # Add a title
    plt.title('TCP RTT Comparison', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save the figure if requested
    if output_file:
        plt.savefig(output_file, dpi=300)
        print(f"Plot saved as {output_file}")
    else:
        output_file = "rtt_comparison.png"
        plt.savefig(output_file, dpi=300)
        print(f"Plot saved as {output_file}")
    
    # Show the plot
    plt.show()

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Compare multiple RTT CSV files with optional iperf3 data.')
    parser.add_argument('files', nargs='+', help='1-3 RTT CSV files to compare')
    parser.add_argument('--iperf', '-i', nargs='*', help='Corresponding iperf3 JSON files')
    parser.add_argument('--labels', '-l', nargs='*', help='Labels for each dataset')
    parser.add_argument('--output', '-o', help='Output file name (PNG)')
    
    args = parser.parse_args()
    
    # Validate number of files
    if len(args.files) > 3:
        print("Error: Maximum 3 RTT files can be compared at once.")
        sys.exit(1)
    
    # Process each RTT file
    rtt_data_list = []
    for csv_file in args.files:
        if not os.path.exists(csv_file):
            print(f"Warning: File {csv_file} not found. Skipping.")
            rtt_data_list.append(None)
            continue
        rtt_data = process_rtt_csv(csv_file)
        rtt_data_list.append(rtt_data)
    
    # Process iperf data if provided
    iperf_data_list = []
    if args.iperf:
        for json_file in args.iperf:
            iperf_data = process_iperf_json(json_file) if json_file and os.path.exists(json_file) else None
            iperf_data_list.append(iperf_data)
    else:
        # No iperf data provided
        iperf_data_list = [None] * len(rtt_data_list)
    
    # Ensure iperf_data_list matches rtt_data_list in length
    while len(iperf_data_list) < len(rtt_data_list):
        iperf_data_list.append(None)
    
    # Create labels
    if args.labels and len(args.labels) == len(rtt_data_list):
        labels = args.labels
    else:
        # Use filenames as labels
        labels = [os.path.splitext(os.path.basename(f))[0] for f in args.files]
    
    # Create the overlay plot
    create_overlay_plot(rtt_data_list, iperf_data_list, labels, args.output)

if __name__ == "__main__":
    main()