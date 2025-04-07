#!/usr/bin/env python3
import sys
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def process_rtt_csv(csv_file):
    """Process the RTT CSV file from tcpdump/tshark."""
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Check if we have the expected columns
        expected_cols = ['frame.time_relative', 'tcp.seq', 'tcp.analysis.ack_rtt']
        if not all(col in df.columns for col in expected_cols):
            print(f"Warning: CSV file missing expected columns. Found: {df.columns}")
        
        # Clean up data - ensure numeric types
        df['frame.time_relative'] = pd.to_numeric(df['frame.time_relative'], errors='coerce')
        df['tcp.analysis.ack_rtt'] = pd.to_numeric(df['tcp.analysis.ack_rtt'], errors='coerce')
        
        # Drop rows with NaN values
        df = df.dropna(subset=['frame.time_relative', 'tcp.analysis.ack_rtt'])
        
        return df
    except Exception as e:
        print(f"Error processing RTT CSV file: {e}")
        sys.exit(1)

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
        
        # Add a zero point if needed for better alignment
        if times and times[0] > 0:
            times.insert(0, 0)
            throughput_values.insert(0, 0)
            
        return {
            'times': times,
            'throughput': throughput_values
        }
    except Exception as e:
        print(f"Warning: Could not process iperf3 JSON file: {e}")
        return None

def create_plot(rtt_data, iperf_data=None, output_prefix=None):
    """Create a time series plot of RTT and optionally throughput."""
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Plot RTT data on primary y-axis
    ax1.plot(rtt_data['frame.time_relative'], rtt_data['tcp.analysis.ack_rtt'], 
             'b-', linewidth=1.2, alpha=0.8, label='RTT')
    ax1.set_xlabel('Time (seconds)', fontsize=12)
    ax1.set_ylabel('Round Trip Time (ms)', color='b', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='b')
    
    # Add vertical lines for bandwidth changes - based on full-test.sh
    markers = [10, 20, 30, 40]  # Script changes bandwidth every 10s
    labels = ['5Mbps→2Mbps', '2Mbps→1Mbps', '1Mbps→500kbps', 'End of test']
    colors = ['red', 'green', 'purple', 'orange']
    
    for i, (marker, label, color) in enumerate(zip(markers, labels, colors)):
        ax1.axvline(x=marker, color=color, linestyle='--', alpha=0.7, label=label)
    
    # If we have iperf data, plot it on secondary y-axis
    if iperf_data and len(iperf_data['times']) > 1:
        ax2 = ax1.twinx()
        ax2.plot(iperf_data['times'], iperf_data['throughput'], 
                 'g-', linewidth=1.5, label='Throughput')
        ax2.set_ylabel('Throughput (Mbps)', color='g', fontsize=12)
        ax2.tick_params(axis='y', labelcolor='g')
        
        # Set y-axis limit to avoid extreme values
        ax2.set_ylim(0, max(iperf_data['throughput']) * 1.1)
    
    # Calculate and add RTT statistics
    rtt_stats = f"Avg RTT: {rtt_data['tcp.analysis.ack_rtt'].mean():.2f} ms\n"
    rtt_stats += f"Min RTT: {rtt_data['tcp.analysis.ack_rtt'].min():.2f} ms\n"
    rtt_stats += f"Max RTT: {rtt_data['tcp.analysis.ack_rtt'].max():.2f} ms\n"
    rtt_stats += f"Std Dev: {rtt_data['tcp.analysis.ack_rtt'].std():.2f} ms"
    
    #plt.figtext(0.02, 0.02, rtt_stats, fontsize=10, 
    #            bbox=dict(facecolor='white', alpha=0.7))
    
    # Add throughput statistics if available
    if iperf_data and len(iperf_data['throughput']) > 1:
        tput_stats = f"Avg Throughput: {np.mean(iperf_data['throughput']):.2f} Mbps\n"
        tput_stats += f"Min Throughput: {np.min(iperf_data['throughput']):.2f} Mbps\n"
        tput_stats += f"Max Throughput: {np.max(iperf_data['throughput']):.2f} Mbps\n"
        tput_stats += f"Total Transfer: {sum(iperf_data['throughput'])/len(iperf_data['throughput'])*len(iperf_data['times']):.2f} Mb"
        
        #plt.figtext(0.02, 0.14, tput_stats, fontsize=10, 
        #           bbox=dict(facecolor='white', alpha=0.7))
    
    # Add title and legend
    title = f"TCP RTT Analysis - {output_prefix}"
    if iperf_data:
        title += " with iperf3 Throughput"
    plt.title(title, fontsize=14)
    
    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    if iperf_data and len(iperf_data['times']) > 1:
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    else:
        ax1.legend(loc='upper right')
    
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save the figure
    if output_prefix:
        output_file = f"{output_prefix}_analysis.png"
    else:
        output_file = "tcp_analysis.png"
    
    plt.savefig(output_file, dpi=300)
    print(f"Plot saved as {output_file}")
    
    # Show the plot
    plt.show()

def main():
    """Main function to handle command line arguments and orchestrate the analysis."""
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f"Usage: {sys.argv[0]} <rtt_csv_file> [iperf3_json_file]")
        sys.exit(1)
    
    rtt_csv_file = sys.argv[1]
    iperf_json_file = sys.argv[2] if len(sys.argv) == 3 else None
    
    # Check if files exist
    if not os.path.exists(rtt_csv_file):
        print(f"Error: RTT CSV file '{rtt_csv_file}' not found.")
        sys.exit(1)
        
    if iperf_json_file and not os.path.exists(iperf_json_file):
        print(f"Warning: iperf3 JSON file '{iperf_json_file}' not found. Continuing with RTT analysis only.")
        iperf_json_file = None
    
    # Get output prefix for the plot filename
    output_prefix = os.path.splitext(os.path.basename(rtt_csv_file))[0]
    
    # Process files
    rtt_data = process_rtt_csv(rtt_csv_file)
    iperf_data = process_iperf_json(iperf_json_file) if iperf_json_file else None
    
    # Print basic info
    print(f"Analyzed {len(rtt_data)} RTT data points")
    if iperf_data:
        print(f"Analyzed {len(iperf_data['times'])} iperf3 intervals")
    
    # Create plot
    create_plot(rtt_data, iperf_data, output_prefix)

if __name__ == "__main__":
    main()