#!/bin/python3

import json
import os
import sqlite3

# Context manager for database connection
class DatabaseConnection:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cur = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cur = self.conn.cursor()
        return self.cur
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()


# Database schema class to hold configuration for a database
class DatabaseSchema:
    # Parse the loaded config and pass the relevant information to the class attributes
    def __init__(self, name, config: dict):
        self.name = name
        self.location = config['location']
        self.table = config['table']
        self.search_columns = config['search']['columns']
        self.search_filters = config['search'].get('filters', dict())
        self.display_columns = config.get('display', {}).get('columns', ['*'])

# Object to perform searches on the database based on the schema class
class DatabaseSearch:
    # Load database schema on initialization
    def __init__(self, schema: DatabaseSchema):
        self.schema = schema

    # Perform search based on the field, value, mode, limit, desired columns and filters provided by the caller
    def search(self, field, value, mode, limit:int = 10, desired_columns:list = ['*'], filters: dict = dict()) -> list:
        columns = ', '.join(desired_columns)  # Join desired columns into a string for SQL query
        table = self.schema.table  # Get table name from schema

        # Construct SQL query based on the search mode and filters
        if mode == 'exact':
            query = f'SELECT {columns} FROM {table} WHERE {field}=? LIMIT ?'
            params = (value, limit)
        elif mode == 'exact_nocase':
            query = f'SELECT {columns} FROM {table} WHERE {field}=? COLLATE NOCASE LIMIT ?'
            params = (value, limit)
        # For like modes, filters are added to the query based on the filters provided by the caller
        elif mode == 'like':
            filters_list = []
            filter_value = []
            for filtr in filters.keys():
                mode = filters[filtr]['mode']
                # Determine the SQL operator based on the filter mode in configuration
                if mode == 'equal':
                    sign = '='
                elif mode == 'less than':
                    sign = '<'
                elif mode == 'greater than':
                    sign = '>'
                # Add multiple filters to the query if they exist
                filters_list.append(f'AND {filtr}{sign}?')
                filter_value.append(filters[filtr]['value'])
            # Construct the final SQL query with filters and limit
            # WARNING! This code assumes that the field names in filters are safe and not user input, otherwise it can lead to SQL injection.
            # Make sure to validate or sanitize field names if they can come from user input.
            query = f'''
                SELECT {columns} FROM {table} WHERE {field} LIKE ?
                {'\n'.join(filters_list)}
                LIMIT ?
            '''
            # Construct parameters for the query, including the value to search for, filter values, and limit
            params = (value, *filter_value, limit)
        # For full-text search mode, the query is constructed to search in the FTS table and then join with the main table based on ROWID,
        # while also applying any filters provided by the caller.
        elif mode == 'fts':
            # Similar to like mode, filters are added to the query based on the filters provided by the caller
            filters_list = []
            filter_value = []
            for filter in filters.keys():
                mode = filters[filter]['mode']
                if mode == 'equal':
                    sign = '='
                elif mode == 'less than':
                    sign = '<'
                elif mode == 'greater than':
                    sign = '>'
                filters_list.append(f'AND {filter}{sign}?')
                filter_value.append(filters[filter]['value'])

            # Get the FTS table name from the schema configuration for the specified field
            fts_table = self.schema.search_columns[field]['fts_table']
            # Construct the final SQL query to perform full-text search with filters and limit.
            # The query searches in the FTS table for matching rows and then retrieves the corresponding records from the main table.
            query = f'''
                SELECT {columns} FROM {table} WHERE ROWID in
                (SELECT ROWID FROM {fts_table} WHERE {field} LIKE ?)
                {'\n'.join(filters_list)}
                LIMIT ?
            '''
            params = (value, *filter_value, limit)
        # Handle unknown search modes by raising an error
        else:
            raise ValueError(f'Unknown search mode: {mode}')

        # Execute the constructed SQL query using the DatabaseConnection context manager and return the results
        with DatabaseConnection(self.schema.location) as cur:
            cur.execute(query, params)
            results = cur.fetchall()
            return results

# Simple function to clear the terminal screen, works for both Windows and Unix-like systems
def clear_terminal():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

# Get user input and handle quit commands
def get_input(text: str):
    inp = input(text)
    if inp == 'q' or inp == 'quit' or inp == '0' or inp == '':
        clear_terminal()
        quit()
    return inp

# prompt user to choose
def select(choices: list, kind: str = ''):
    clear_terminal()
    # If there is only one choice, return it without prompting the user
    if len(choices) == 1:
        return choices[0]
    # Otherwise, display the choices and prompt the user to select one by entering its number
    print(f'Available {kind}s:')
    for i,choice in enumerate(choices, start=1):
        print(f'\t{i}. {choice}')

    # Loop until the user enters a valid choice number corresponding to one of the available choices
    while True:
        try:
            choice = int(get_input(f'Select {kind} number: '))
            if 1 <= choice <= len(choices):
                choice = choices[choice-1]
                break
            else:
                print('Invalid choice!')
        except ValueError:
            print('Please enter a valid number!')

    return choice

def select_filters(filters_schema: dict):
    filters = dict()
    # Prompt the user to decide if they want to use filters for their search.
    use_filters = get_input('Search using filters? (y/n): ')
    if use_filters == 'n': return dict()
    while True:
        filter = select(list(filters_schema.keys()), 'filter')
        mode = select(filters_schema[filter]['modes'], 'filter mode')
        value = select_value(filter, mode)
        filters[filter] = {'mode': mode, 'value': value}
        add_filters = get_input('Use more filters? (y/n): ')
        if add_filters == 'n': break
    return filters

def select_value(field: str, filter_mode: str = None):
    # Prompt the user to enter the value to search for, with a different prompt whether it's for a filter or not
    value = get_input(f'Enter {field}\'s value to search: ') if not filter_mode else get_input(f'Enter {field}\'s value to be {filter_mode}: ')
    return value

# Function to convert the raw results from the database into a list of dictionaries for easier display, using the headers provided
def display_data(results, headers):
    # Zip the headers and results together to create a list of dictionaries
    zipped = []
    for i,result in enumerate(results, start=1):
        record = dict()
        for field,value in zip(headers, result):
            record[field] = value
        zipped.append(record)
    return zipped
            
# Function to display the search results in a user-friendly format,
# allowing the user to navigate through the records using next(n) and previous(N) commands
def display(data: dict):
    idx = 0
    inp = ''
    l = len(data)-1
    if l < 0: 
        print('Found no records.')
        return
    else:
        print(f'Found {l+1} records')
        input('Press Enter to continue ')
    while inp != 'q':
        clear_terminal()
        print(f'{idx+1}.')
        for field in data[idx].keys():
            print(f'\t{field}:\t{'No Value' if data[idx][field] == None else data[idx][field]}')
        inp = input('(n/N/q): ')
        if inp.isdigit():
            pgn = int(inp)
            if pgn <= l+1 and pgn >= 0:
                idx = pgn-1
            else:
                print('Invalid number!')
        elif inp == 'n':
            idx += 1
            if idx > l:
                idx = 0
        elif inp == 'N':
            idx -= 1
            if idx < 0:
                idx = l
        else:
            break
            

if __name__ == '__main__':
    # Load database configurations
    with open('config.json', 'r') as f:
        databases = json.load(f)

    # Loading databese schema
    db_key = select(list(databases.keys()), 'database') # Select database
    schema = DatabaseSchema(db_key, databases[db_key]) # Load database schema
    searcher = DatabaseSearch(schema) # Create searcher object
    
    # Get search parameters from user
    field = select(list(schema.search_columns.keys()), 'field') # Select field to search
    mode = select(schema.search_columns[field]['modes'], 'mode') # Select search mode
    value = select_value(field) # Get value to search for

    # Get filters if needed
    filters = dict()
    if mode == 'like':
        filters = select_filters(schema.search_filters) # Get filters for like mode
    elif mode == 'fts':
        value = '%' + value.replace(' ', '%') + '%' # Replace spaces with % for fts search wildcard
        filters = select_filters(schema.search_filters) # Get filters for fts mode
    else:
        pass

    # Perform search and display results default limit is 20
    results = searcher.search(field, value, mode, limit=20, filters=filters, desired_columns=schema.display_columns)

    # Fetch headers for display from display_columns, handling aliases if they exist
    headers = []
    for header in schema.display_columns:
        if ' AS ' in header:
            # Extract alias from header
            alias = header.split(' AS ')[-1].strip()
            if alias.startswith('\"') and alias.endswith('\"'):
                alias = alias[1:-1] # Remove surrounding double quotes
            elif alias.startswith('\'') and alias.endswith('\''):
                alias = alias[1:-1] # Remove surrounding single quotes
            headers.append(alias) # Append alias to headers
        else:
            headers.append(header.strip()) # Append original header if no alias

    # if there are no results, inform the user and exit
    if display_data(results, headers) == []:
        print('Found no records.')
        exit()

    # create displayable data and display it
    displayable = display_data(results, headers)
    display(displayable)
    exit()