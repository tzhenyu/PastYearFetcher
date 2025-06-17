# Past Year Fetcher

**Past Year Fetcher** is a simple tool to fetch past year examination papers from TAR UMT's ePrints system. It allows students to search for past year papers by course code and filter by faculty, then download the papers directly.

## How to use

1. **Enter Your TAR UMT Credentials**: You need to provide your TAR UMT username and password to access the ePrints system.
2. **Search for Papers**: Input a course code (e.g., `BACS1013`) and optionally filter by faculty.
3. **Download Papers**: Once results are found, you can download the past year papers directly through the interface.

This project does not store any of your credentials or data. All requests are made directly to TAR UMT's ePrints server, and downloaded files are not saved locally by this tool.

## How it works
It takes the advantage of RSS feature of ePrints system, that fetch search results in XML format. The script can extract the information needed and prepare the download links from it. More info in the source code.

## Disclaimer

> ⚠️ This is a personal project and is **not affiliated with TAR UMT** in any way. Use at your own risk.  
> The developer assumes no responsibility for any issues arising from the use of this tool.  
> Please respect TAR UMT's terms of use and only use this tool for educational purposes.

