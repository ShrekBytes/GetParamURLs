### Short Summary Description

**GetParamURLs** is a Python script designed for bug bounty hunters and security researchers. It leverages `gau` and `waybackurls` to discover endpoints of a given domain and filters out URLs that contain query parameters. The script further refines the list by removing MIME-type files and duplicate links based on endpoints and parameters.

### README.md

```markdown
# GetParamURLs

GetParamURLs is a Python script designed for bug bounty hunters and security researchers to find URLs with query parameters for a given domain. It uses `gau` and `waybackurls` to gather endpoints, filters out unwanted MIME-type files, and removes duplicate links to provide a clean list of potential targets.

## Features

- Gathers endpoints using `gau` and `waybackurls`
- Filters URLs that contain query parameters
- Removes URLs with unwanted MIME-type extensions
- Eliminates duplicate links based on endpoints and parameters
- Deletes intermediate files to keep the workspace clean

## Requirements

- Python 3.x
- `gau` (Get All URLs)
- `waybackurls`

## Installation

1. Ensure you have Python 3.x installed on your system.
2. Install `gau`:
   ```sh
   go install github.com/lc/gau/v2/cmd/gau@latest
   ```
3. Install `waybackurls`:
   ```sh
   go get github.com/tomnomnom/waybackurls
   ```

## Usage

1. Clone the repository:
   ```sh
   git clone https://github.com/yourusername/GetParamURLs.git
   cd GetParamURLs
   ```
2. Run the script:
   ```sh
   python3 GetParamURLs.py example.com
   ```

## Script Overview

```python
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
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -am 'Add new feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Create a new Pull Request.

## Acknowledgements

- [gau](https://github.com/lc/gau)
- [waybackurls](https://github.com/tomnomnom/waybackurls)

## Contact

For any issues or feature requests, please open an issue on GitHub.
```

This README file provides a comprehensive guide for users to understand, install, and use your script effectively.
