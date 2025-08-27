# Past Year Fetcher

**Past Year Fetcher** is a lightweight tool that simplifies downloading past year examination papers from **TAR UMT’s ePrints system**.

## Why Not Just Use ePrints?

| **ePrints System**                              | **Past Year Fetcher**                    |
| ----------------------------------------------- | ---------------------------------------- |
| Log in twice just to get access                 | Log in once, then fetch everything       |
| Download papers one by one with repeated clicks | Download all matching papers in one go   |
| Duplicate filenames, requiring manual renaming  | Files auto-named by subject, month, year |
| Slow, multi-step workflow                       | Instant, clean, and efficient            |

## Features

* **One login, instant access** – no more logging in twice.
* **Batch downloads** – get all matching papers at once.
* **Smart naming** – files are auto-named by *subject, month, year* for easy reference.
* **Search & filter** – find papers by course code and faculty.


## How to Use

1. **Login** – Enter your TAR UMT username and password (needed to access ePrints).
2. **Search** – Input a course code (e.g., `BACS1013`), and optionally filter by faculty.
3. **Download** – Instantly fetch all matching papers in an organized format.

## How It Works

The tool uses the **RSS feed feature** of TAR UMT’s ePrints system. Search results are pulled in XML format, parsed by the script, and converted into direct download links. Check the source code for details.


## Disclaimer

This is a **personal project** and is **not affiliated with TAR UMT**.

* Credentials are **not stored** — all requests go directly to the ePrints server.
* Downloaded files are not saved locally by this tool.
* Use at your own risk, and only for educational purposes in line with TAR UMT’s terms of use.

