# SQLite Python CLI browser and search.
This project is designed to make your big sqlite multi-table databases browsable easily.
You don't need to install DB browsers like sqlite-browser. You don't even need to know about sql queries!

## Highlists
Here are the main takeaways of this guide:
* Overview: What does this project do.
* Quick Start: How to set up your own config.json
* Usage: Executing the code and exploring the minimal CLI enviroment.
* Advanced Configurations (Hardcoded Parameters)
* Warnings: Some important warnings you need to know if you want to use this script for an enterprise project.
* ToDos: Features I want to add later.

## Overview
This project has been written in python for reading SQLite databases.
It purpose is not and it cannot write or modify databases. It has a read only usage.

It can be configured for multi-table search, and the search methods are:
1. exact
2. exact_nocase
which filters cannot be applied on.
3. like
4. FTS (Fast Text Search)
which can be searched using the filters to limit the results.

Search filters are designed to be simple and are available in 3 modes:
1. equal
which matches the value exactly
2. greater than
which matches the values greater than users input
3. less than

### Files diagram:
```bash
SQLitePythonCLI
├── config.example.json
├── config.json
├── dbbrowser.py
└── README.md
```

The configurations are in config.json file, we'll get to the configuration in the next step.

## Quick Start
First make a copy of config.example.json named to example.json
```bash
cp config.example.json config.json
```
Then you have to edit the "config.json" using your favorite text editor.
For example, using nano:
```bash
nano config.json
```
and you enter the configuration json file.
```json
{
  "DATABASE_DISPLAY_NAME1": {
    "location": "PATH_TO_DB",
    "table": "TABLE_NAME",
    "search": {
      "columns": {
        "FIELD1": { "modes": ["exact", "like"] },
        "FIELD2": { "modes": ["fts"], "fts_table": "FTS_TABLE_NAME" },
        "FIELD3": { "modes": ["exact_nocase"] }
      },
      "filters": {
        "FILTER_FIELD_NAME2": { "modes": ["less than", "equal", "greater than"] }
      }
    },
    "display": {
      "columns": [
        "FIELD1 AS \"Display Name 1\"",
        "FIELD2 AS \"Display Name 2\"",
        "FIELD3"
      ]
    }
  }
}
```

I explain each key or value to configure for your own usage.
(Note that only the stuff written in ALL_CAPITAL can be customized)

### Database and table main values
* DATABASE_DISPLAY_NAME1: replace with the name you want to user see in CLI.
* PATH_TO_DB: replace with the path to your database.
* TABLE_NAME: replace with the table which is wanted to be search in the database file.

Please note that for multi-table in search in the same file, you have to define an element for each table with different *DATABASE_DISPLAY_NAME*.

### Search configuration
The array **search** consists of two elements (which are array themselves).
The key *columns* is for adding the sql fields you want to be available for user search.
* FIELD1: replace with the exact field's name you want to be searched (e.g NAME).
* modes: currently there are four available search modes:
    * exact: matches the values exactly.
    * exact_nocase: matches the value exactly, but case ignorant.
    * like: for regex and wildcards search (regex must be input by user)
    * fts: to search texts in fts mode, inputs ' ' are replaced with wildcards so each space will be a delimiter.
The key *filters* is for adding the sql fields you want to be available for search filters.
* FILTER_FIELD_NAME2: replace with the fields name you want the filter to be applied on.
* modes: currently three modes are available which I explained briefly on previous section:
    * equal
    * less than
    * greater than

After you have your config.json made, navigate through the next step.
### Display Configuration
You can place a prettifier SQL in the columns key to display pretty names to the user.
e.g:
```json
"display": {
    "columns": [
        "printf('%007d', NATIONAL_CODE) AS \"National Code\"",
        "FULL_NAME_DISPLAY AS \"Full Name\"",
        "printf('%010d', MOBILE) AS \"Phone Number\""
    ]
}
```

## Usage
1. Give the code executable permission:
```bash
chmod +x ./dbbrowser.py
```
2. Run it:
```bash
./dbbrowser.py
```
3. Select the table number you want to search in (e.g It is customers informations):
```bash
1
```
4. Select the field number of the table you want to search in (e.g phone number):
```bash
2
```
5. Now you have to enter the fields value to search (e.g 09123456789):
```bash
09123456789
```

6. The next step depends on whether there are results matching your search or not.
    * if there are not:
```bash
Found no records.
```
    * if there are:
```bash
Found 2 records
Press Enter to continue 
```
    after pressing enter, each result will be shown in a different page, you can navigate between pages using n (for next page) or N (for previous page). You can also quit entering q or blank enter. Page numbers can also be entered.

## Advanced Configurations
There are some parameters which are hard coded and are not available in config.json.
Important ones are all placed in the main block so you won't need to change them if importing this script in another one.
1. limit: changes the maximum matching records to fetch.
```python
    results = searcher.search(field, value, mode, limit=20, filters=filters, desired_columns=schema.display_columns)
```

## Warnings
There are some important things to know for data protection.
1. If you prompt user for the fields, filterfields or table name directly, consider making the queries SQL-Injection safe or validate the date. It also happens if you don't validate config.json if it is user input.
2. FTS are is replacing each space for a '%' which results to wildcard searching, because my table fts fields words where not seperated by spaces.

## ToDos:
* Define a class for user input manipulation
* Define a class for displaying data
* User-friendly config.json generation and install.sh creation.
* Add telegram bots api to search the DBs.

## License:
This project is licensed under the GNU GPLv3 License - see the LICENSE file for details