import os
import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV file
dirname = os.path.dirname(__file__)
file_path = os.path.join(dirname, 'output.csv')
data = pd.read_csv(file_path)

# Step 1: Sort the data by the 'pod_end' column
data_sorted = data.sort_values(by='pod_end')

# Step 2: Normalize the 'pod_end' column
pod_end_first = data_sorted['pod_end'].iloc[0]
data_sorted['normalized_pod_end'] = (data_sorted['pod_end'] - pod_end_first) / 1000000

# Step 3: Plot the graph by sorting order
plt.figure(figsize=(10, 6))
plt.plot(
    range(len(data_sorted)),  # X-axis: Sorting order
    data_sorted['normalized_pod_end'],  # Y-axis: Normalized pod_end
    marker='o',
    linestyle='-',
    color='b',
    label='Normalized Pod End Time'
)
plt.title('Normalized Pod End Time by Starting Instance', fontsize=14)
plt.xlabel('Starting Instance', fontsize=12)
plt.ylabel('Normalized Pod End Time (ms)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(fontsize=10)
plt.tight_layout()
plt.show()
