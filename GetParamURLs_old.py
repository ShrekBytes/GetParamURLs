import os
import sys
import subprocess
from urllib.parse import urlparse, parse_qs


# Function to delete files, handling exceptions
def delete_files(*files):
    for file in files:
        try:
            os.remove(file)
            print(f"File '{file}' deleted successfully.")
        except FileNotFoundError:
            print(f"File '{file}' not found. Skipping deletion.")
        except Exception as e:
            print(f"Error deleting file '{file}': {e}")


# Function to save links to a file
def save_to_file(links, output_file):
    with open(output_file, 'a') as file:
        for link in links:
            file.write(link + '\n')
    print(f"Filtered links appended to {output_file}")


# Function to filter out duplicate links
def filter_links_final(links):
    """
    Filter out duplicate links based on endpoint and sorted parameters.
    Parameters:
    - links (list): List of strings representing URLs.
    Returns:
    - unique_links (list): List of unique URLs after deduplication.
    """
    seen = set()
    unique_links = []
    for link in links:
        parsed_url = urlparse(link)
        endpoint = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
        params = dict(parse_qs(parsed_url.query))
        key = (endpoint, tuple(sorted(params.keys())))
        if key not in seen:
            seen.add(key)
            unique_links.append(link)
    return unique_links


# Check if the correct number of arguments is provided
if len(sys.argv) != 2:
    print("Usage: python3 script_name.py example.com")
    sys.exit(1)

# Get the domain from command-line arguments
domain = sys.argv[1]

# Display the user input
print("Domain:", domain)

GAU_FILE = domain + "_gau.txt"
WAYBACKURLS_FILE = domain + "_waybackurls.txt"
MERGED_FILE = domain + "_merged.txt"
UNIQUE_FILE = domain + "_unique.txt"
PARAMETERS_FILE = domain + "_parameters.txt"
NO_MIMES_FILE = domain + "_no_mimes.txt"

# List of commands to be executed sequentially
commands = [
    f"gau --o {GAU_FILE} {domain}",
    f"waybackurls {domain} > {WAYBACKURLS_FILE}",  # collects all urls
    f"cat {GAU_FILE} {WAYBACKURLS_FILE} > {MERGED_FILE}",
    f"sort -u {MERGED_FILE} -o {UNIQUE_FILE}",  # removes duplicate urls
    f"grep '=' {UNIQUE_FILE} > {PARAMETERS_FILE}",  # removes urls without parameters
    rf"""grep -E -v '/[^?&/]*\.(jpg|jpeg|JPG|heic|mp4|mp3|mkv|m4a|gif|webp|eot|css|json|woff|woff2|ttf|svg|eof|pdf|png|js|avi|pptx|docx)([?&]|$)' {PARAMETERS_FILE} > {NO_MIMES_FILE}"""
]

# Execute each command in the list
for command in commands:
    subprocess.run(command, shell=True, check=True)

with open(NO_MIMES_FILE, 'r') as file:
    # Each line is stripped of leading and trailing whitespaces using line.strip()
    stripped_links = [line.strip() for line in file]

filtered_links = filter_links_final(stripped_links)

# Delete intermediate files
delete_files(GAU_FILE, WAYBACKURLS_FILE, MERGED_FILE, UNIQUE_FILE, PARAMETERS_FILE, NO_MIMES_FILE)

# Save filtered and unique links to a new file
save_to_file(filtered_links, f"{domain}.txt")
