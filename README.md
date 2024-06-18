# GetParamURLs

**GetParamURLs** is a Python script for bug bounty hunters that finds URLs with query parameters using gau and waybackurls, filters out unwanted MIME types, and removes duplicates so that you can focus only on what is important.

## Features

- Gathers endpoints using `gau` and `waybackurls`
- Filters URLs that contain query parameters
- Removes URLs with unwanted MIME-type extensions
- Eliminates duplicate links based on endpoints and parameters

**Prerequisites:**

* Python 3.x
* `gau` (Get All URLs) - Installation instructions can be found [here](https://github.com/lc/gau)
* `waybackurls` - Installation instructions can be found [here](https://github.com/tomnomnom/waybackurls)

## Usage

1. Clone the repository:

    ```sh
    git clone https://github.com/ShrekBytes/GetParamURLs.git
    ```

2. Change into the repository directory:

    ```sh
    cd GetParamURLs
    ```

3. Run the script:

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
