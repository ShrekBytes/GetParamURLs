import os
import re
import sys
import subprocess
from urllib.parse import urlparse, parse_qs


# Function to filter URLs with query parameters
def filter_urls_with_params(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            url = line.strip()
            if urlparse(url).query:
                outfile.write(url + '\n')


# Function to remove MIME files based on extensions
def remove_mime_files(input_file, output_file):
    mime_extensions = {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'mkv', 'pdf', 'pptx', 'ppt', 'heic',
                       'mp3', 'm4a', 'webp', 'eot', 'css', 'json', 'woff', 'woff2', 'ttf', 'svg', 'eof', 'js', 'docx',
                       'key'}
    pattern = r'\/([^\/?#]+)\.(%s)(\?[^\/]*$|\/[^\/]*$|#.*$|$)' % '|'.join(mime_extensions)
    regex = re.compile(pattern, re.IGNORECASE)

    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for url in infile:
            url = url.strip()
            if not regex.search(url):
                outfile.write(url + '\n')


# Function to remove duplicate links based on endpoint and parameters
def remove_duplicates(input_file, output_file):
    seen = set()
    unique_links = []
    with open(input_file, 'r') as infile:
        for line in infile:
            url = line.strip()
            parsed_url = urlparse(url)
            endpoint = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            params = dict(parse_qs(parsed_url.query))
            key = (endpoint, tuple(sorted(params.keys())))
            if key not in seen:
                seen.add(key)
                unique_links.append(url)

    with open(output_file, 'w') as outfile:
        for link in unique_links:
            outfile.write(link + '\n')


# Function to delete files
def delete_files(*files):
    for file in files:
        try:
            os.remove(file)
            print(f"File '{file}' deleted successfully.")
        except FileNotFoundError:
            print(f"File '{file}' not found. Skipping deletion.")
        except Exception as e:
            print(f"Error deleting file '{file}': {e}")


# Main workflow
def main():
    # Check if the correct number of arguments is provided
    if len(sys.argv) != 2:
        print("Usage: python3 script_name.py example.com")
        sys.exit(1)

    # Get the domain from command-line arguments
    domain = sys.argv[1]
    print("Domain:", domain)

    # Define filenames based on the domain
    gau_file = f"{domain}_gau.txt"
    waybackurls_file = f"{domain}_waybackurls.txt"
    merged_file = f"{domain}_merged.txt"
    parameters_file = f"{domain}_parameters.txt"
    no_mimes_file = f"{domain}_no_mimes.txt"
    output_file = f"{domain}.txt"

    # List of commands to be executed sequentially
    commands = [
        f"gau --o {gau_file} {domain}",
        f"waybackurls {domain} > {waybackurls_file}",
        f"cat {gau_file} {waybackurls_file} > {merged_file}",
    ]

    # Execute each command in the list
    for command in commands:
        subprocess.run(command, shell=True, check=True)

    # Filter URLs with query parameters
    filter_urls_with_params(merged_file, parameters_file)

    # Remove MIME files
    remove_mime_files(parameters_file, no_mimes_file)

    # Remove duplicate URLs
    remove_duplicates(no_mimes_file, output_file)

    # Delete intermediate files
    delete_files(gau_file, waybackurls_file, merged_file, parameters_file, no_mimes_file)


# Entry point of the script
if __name__ == "__main__":
    main()
