# GetParamURLs

GetParamURLs is a Python script for bug bounty hunters that `finds URLs with query parameters` using gau and waybackurls, filters out unwanted MIME types, and removes duplicates so that you can focus only on what is important.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Features

- Gathers endpoints using `gau` and `waybackurls`
- Filters URLs that contain query parameters
- Removes URLs with unwanted MIME-type extensions
- Eliminates duplicate links based on endpoints and parameters
- Saves filtered juicy URLs to domain.txt file

## Prerequisites

- Python 3.x
- `gau` (Get All URLs) - Installation instructions can be found [here](https://github.com/lc/gau)
- `waybackurls` - Installation instructions can be found [here](https://github.com/tomnomnom/waybackurls)

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

## Contributing

To contribute, fork the repository, make your changes, and submit a pull request to add features or improve existing ones. Your contributions are appreciated!

## License

"License? Nah, who needs those bothersome regulations anyway? Feel free to do whatever you want with this code – use it as a doorstop, launch it into space, or frame it as a modern art masterpiece. Just don't blame me if things get a little wild!"
