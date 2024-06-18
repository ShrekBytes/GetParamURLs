# GetParamURLs

**GetParamURLs** is a Python script for bug bounty hunters that finds URLs with query parameters using gau and waybackurls, filters out unwanted MIME types, and removes duplicates so that you can focus only on what is important.

### README.md

```markdown
# GetParamURLs

GetParamURLs is a Python script designed for bug bounty hunters and security researchers to find URLs with query parameters for a given domain. It uses `gau` and `waybackurls` to gather endpoints, filter out unwanted MIME-type files, and remove duplicate links to provide a clean list of potential targets.

## Features

- Gathers endpoints using `gau` and `waybackurls`
- Filters URLs that contain query parameters
- Removes URLs with unwanted MIME-type extensions
- Eliminates duplicate links based on endpoints and parameters

## Requirements

- Python 3.x
- `gau` (Get All URLs)
- `waybackurls`

## Usage

1. Clone the repository:
   ```sh
   git clone https://github.com/ShrekBytes/GetParamURLs.git
   cd GetParamURLs
   ```
2. Run the script:
   ```sh
   python3 GetParamURLs.py example.com
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
