#!/usr/bin/env python3
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import pandas as pd
import os.path

def plot_rtt_and_throughput(rtt_csv, iperf_json=None):
    """Plot RTT data and optionally iperf3 throughput data on the same plot."""
    
    # Check if RTT file exists
    if not os.path.isfile(rtt_csv):
        print(f"Error: RTT file {rtt_csv} not found")
        return

    # Extract filename without extension for output
    base_name = os.path.splitext(os.path.basename(rtt_csv))[0]
    
    # Read RTT data
    try:
        # Read CSV file
        data = pd.read_csv(rtt_csv)
        
        # If there are no column headers, assign them
        if len(data.columns) == 2 and data.columns[0] != 'time' and data.columns[0] != 'Time':
            data.columns = ['time', 'rtt']
        
        # Drop any rows with NaN values
        data = data.dropna()
        
        # Convert time and rtt to float if needed
        data['time'] = data['time'].astype(float)
        data['rtt'] = data['rtt'].astype(float)
        
    except Exception as e:
        print(f"Error reading RTT data: {e}")
        return
    
    # Create the figure with primary y-axis for RTT
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Plot RTT vs Time using lines on primary y-axis
    line1 = ax1.plot(data['time'], data['rtt'], '-', linewidth=1.0, color='blue', label='RTT (ms)')
    ax1.set_xlabel('Time (seconds)', fontsize=12)
    ax1.set_ylabel('Round Trip Time (ms)', fontsize=12, color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    
    # Add vertical lines for bandwidth changes
    ax1.axvline(x=10, color='red', linestyle='--', label='15Mbit → 7Mbit')
    ax1.axvline(x=25, color='green', linestyle='--', label='7Mbit → 2Mbit')
    ax1.axvline(x=40, color='purple', linestyle='--', label='2Mbit → 600kbit')
    
    # If iperf3 JSON file is provided, add throughput data on secondary y-axis
    if iperf_json and os.path.isfile(iperf_json):
        try:
            # Read the JSON file
            with open(iperf_json, 'r') as f:
                iperf_data = json.load(f)
            
            # Extract intervals data
            intervals = iperf_data.get('intervals', [])
            
            # Extract time and throughput data
            throughput_times = []
            throughput_values = []
            
            for interval in intervals:
                # Get the end time and throughput from each interval
                end_time = interval['sum']['end']
                bits_per_second = interval['sum']['bits_per_second']
                
                throughput_times.append(end_time)
                # Convert to Mbps for readability
                throughput_values.append(bits_per_second / 1e6)
            
            # Create secondary y-axis for throughput
            ax2 = ax1.twinx()
            line2 = ax2.plot(throughput_times, throughput_values, '-', 
                             linewidth=1.5, color='green', label='Throughput (Mbps)')
            ax2.set_ylabel('Throughput (Mbps)', fontsize=12, color='green')
            ax2.tick_params(axis='y', labelcolor='green')
            
            # Add throughput statistics
            throughput_array = np.array(throughput_values)
            throughput_stats = f"Avg Throughput: {np.mean(throughput_array):.2f} Mbps\n"
            throughput_stats += f"Max Throughput: {np.max(throughput_array):.2f} Mbps\n"
            throughput_stats += f"Min Throughput: {np.min(throughput_array):.2f} Mbps"
            
            plt.figtext(0.02, 0.12, throughput_stats, fontsize=10,
                        bbox=dict(facecolor='white', alpha=0.7))
            
            # Combine legends from both axes
            lines = line1 + line2
            labels = [l.get_label() for l in lines]
            ax1.legend(lines, labels, loc='upper right')
        
        except Exception as e:
            print(f"Error processing iperf3 data: {e}")
            # Still show the RTT plot
            ax1.legend()
    else:
        # If no iperf data, just show RTT legend
        ax1.legend()
    
    # Add RTT statistics
    rtt_stats = f"Avg RTT: {data['rtt'].mean():.2f}ms\n"
    rtt_stats += f"Min RTT: {data['rtt'].min():.2f}ms\n"
    rtt_stats += f"Max RTT: {data['rtt'].max():.2f}ms\n"
    rtt_stats += f"Std Dev: {data['rtt'].std():.2f}ms"
    
    plt.figtext(0.02, 0.02, rtt_stats, fontsize=10,
                bbox=dict(facecolor='white', alpha=0.7))
    
    # Add title
    title = f'TCP Analysis - {base_name}'
    if iperf_json:
        title += f' with iperf3 throughput'
    plt.title(title, fontsize=14)
    
    # Add grid
    ax1.grid(True, alpha=0.3)
    
    # Save the figure
    suffix = '_with_throughput' if iperf_json else '_lineplot'
    output_file = f"{base_name}{suffix}.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Plot saved as {output_file}")
    
    # Show the plot
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f"Usage: {sys.argv[0]} <rtt_csv_file> [iperf3_json_file]")
        sys.exit(1)
    
    rtt_csv = sys.argv[1]
    iperf_json = sys.argv[2] if len(sys.argv) == 3 else None
    
    plot_rtt_and_throughput(rtt_csv, iperf_json)
