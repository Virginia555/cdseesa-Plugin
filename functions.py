import subprocess
from docker import from_env
from docker.errors import DockerException
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

#Dictionary with the descriptions of the tests to display
descriptions = {
  "TC101": "Service Reachability",
  "TC201": "Basic Query",
  "TC301": "Single Remote Online Download",
  "TC102": "Test 2.1",
  "TC202": "Complex Query (Geo-Time Filter)",
  "TC302": "Multiple Remote Online Download"
}

def is_docker_running():
    try:
        client = from_env()
        client.ping()  # Attempts to ping the Docker daemon
        print("Docker is running.")
        return True
    except DockerException:
        print("Docker is not running.")
        return False

def run_command(command):
    process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(process.stdout.decode())
    return process

def check_container_exists(name):
    client = from_env()
    container_list = client.containers.list(all=True)
    for container in container_list:
        if name == container.name:
            return True
    return False

#Generate a results array from the json files to be rendered by the template
def generate_results(results_files):
    results = []

    for json_file in results_files:
        provider = json_file.split('-')[-2]
        if os.path.exists(json_file):
            with open(json_file, 'r') as file:
                data = json.load(file)
                for result in data.get('testCaseResults', []):
                    result['provider'] = provider
                    result['description'] = descriptions[result['testName']]
                    results.append(result)

    return results

def run_tests(container_name = "testsite-1", tests = ["TS01"], providers = ["cdse"], remove_container = True):

    #If docker is not running the returned false will trigger on app.py a redirection to /error/docker
    if not is_docker_running():
        return False 

    results_files = []

    for provider in providers:

        if not check_container_exists(container_name):
            print(f"Creating container {container_name}...")
            run_command(f"docker run --detach --name {container_name} ghcr.io/esacdab/cdab-testsuite:latest")
        else:
            print(f"Container {container_name} already exists. Continuing without creating a new one.")
            run_command(f"docker start {container_name}")

        run_command(f"docker cp config.yaml {container_name}:/home/jenkins/config.yaml")

        for test in tests:
            print(f"Executing {test} on {provider}...")
            run_command(f"docker exec {container_name} cdab-client -v -tsn={container_name} -tn={provider} {test}")

            result_file = f"{container_name}-{test}-{provider}-results.json"
            results_dir = os.path.join(os.path.dirname(__file__), 'Results')
            os.makedirs(results_dir, exist_ok=True)  # Creates the directory if it does not exist
            local_result_file = os.path.join(results_dir, result_file)
            print(f"Copying results for {test} from {provider}...")
            run_command(f"docker cp {container_name}:/home/jenkins/{test}Results.json {local_result_file}")
            results_files.append(local_result_file)
    
    if remove_container:
        print(f"Stopping and removing container {container_name}...")
        run_command(f"docker stop {container_name}")
        run_command(f"docker rm {container_name}")

    return generate_results(results_files)

def plot_time_series(df, row_to_highlight=False):
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    df = df.sort_values(by='Date')

    # Select numeric columns for daily average calculation
    cols_to_include = df.select_dtypes(include=['number']).columns.tolist()
    

    # Calculate daily averages for numeric columns only
    daily_avg = df[cols_to_include].groupby(df['Date'].dt.date).mean().reset_index()
    daily_avg['Date'] = pd.to_datetime(daily_avg['Date'])

    fig, axs = plt.subplots(2, 1, figsize=(10, 10))

    # Response Time Plot
    axs[0].plot(daily_avg['Date'], daily_avg['avgResponseTime'], label='Daily Average Response Time', marker='o', linestyle='-')
    axs[0].plot(daily_avg['Date'], daily_avg['peakResponseTime'], label='Daily Average Peak Response Time', marker='x', linestyle='-')
    axs[0].xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
    axs[0].xaxis.set_major_locator(mdates.DayLocator())
    axs[0].set_title('Response Time Over Time')
    axs[0].set_xlabel('Date')
    axs[0].set_ylabel('Time (milliseconds)')
    axs[0].legend()
    axs[0].grid(True)


    # Highlight a specific row if indicated
    if row_to_highlight:
        axs[0].scatter(df.iloc[row_to_highlight]['Date'], df.iloc[row_to_highlight]['avgResponseTime'], color='blue', zorder=5)
        axs[0].scatter(df.iloc[row_to_highlight]['Date'], df.iloc[row_to_highlight]['peakResponseTime'], color='red', zorder=5)
        # Define custom legend handles
        legend_handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='Your Avg Response Time'),
                        Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='Your Peak Response Time')]

        # Combine custom handles with existing handles
        handles, labels = axs[0].get_legend_handles_labels()
        handles.extend(legend_handles)

        # Display the legend
        axs[0].legend(handles=handles)

    # Concurrency Plot
    axs[1].plot(daily_avg['Date'], daily_avg['avgConcurrency'], label='Daily Average Concurrency', marker='o', linestyle='-')
    axs[1].plot(daily_avg['Date'], daily_avg['peakConcurrency'], label='Daily Average Peak Concurrency', marker='x', linestyle='-')
    axs[1].xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
    axs[1].xaxis.set_major_locator(mdates.DayLocator())
    axs[1].set_title('Concurrency Over Time')
    axs[1].set_xlabel('Date')
    axs[1].set_ylabel('Concurrency')
    axs[1].legend()
    axs[1].grid(True)

    # Highlight a specific row if indicated
    if row_to_highlight:
        axs[1].scatter(df.iloc[row_to_highlight]['Date'], df.iloc[row_to_highlight]['avgConcurrency'], color='blue', zorder=5)
        axs[1].scatter(df.iloc[row_to_highlight]['Date'], df.iloc[row_to_highlight]['peakConcurrency'], color='red', zorder=5)

        legend_handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='Your Avg Concurrency'),
                        Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='Your Peak Concurrency')]

        # Combine custom handles with existing handles
        handles, labels = axs[0].get_legend_handles_labels()
        handles.extend(legend_handles)

        # Display the legend
        axs[1].legend(handles=handles)

    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save plots as images
    plots_dir = os.path.join(os.path.dirname(__file__), f'static\plots')
    os.makedirs(plots_dir, exist_ok=True)  # Creates the directory if it does not exist
    plots_file = os.path.join(plots_dir, 'time_series_plots.png')
    plt.savefig(plots_file)

def plot_scatter(df, row_to_highlight=False):
    plt.figure(figsize=(10, 6))
    plt.title('Average Response Time vs. Average Concurrency')
    plt.xlabel('Average Concurrency')
    plt.ylabel('Average Response Time (milliseconds)')
    plt.grid(True)
    
        # Highlight a specific row if indicated
    if row_to_highlight:
        plt.scatter(df.drop(row_to_highlight)['avgConcurrency'], df.drop(row_to_highlight)['avgResponseTime'], color='blue', s=50)
        my_point = plt.scatter(df.loc[row_to_highlight, 'avgConcurrency'], df.loc[row_to_highlight, 'avgResponseTime'], color='red', s=100, label='Your Result')  # Larger and red dot
        plt.legend(handles=[my_point])
    else:
        plt.scatter(df['avgConcurrency'], df['avgResponseTime'], color='blue', s=50)  # s is the size of the dots

    plt.gca().invert_yaxis()

    # Save plots as images
    plots_dir = os.path.join(os.path.dirname(__file__), f'static\plots')
    os.makedirs(plots_dir, exist_ok=True)  # Creates the directory if it does not exist
    plots_file = os.path.join(plots_dir, 'time_series_plots.png')
    plt.savefig(plots_file)

if __name__ == "__main__":
    run_tests()
