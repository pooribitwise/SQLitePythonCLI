#!/bin/python3

import os
import json
import sqlite3

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


class DatabaseSchema:
    def __init__(self, name, config: dict):
        self.name = name
        self.location = config['location']
        self.table = config['table']
        self.search_columns = config['search']['columns']
        self.search_filters = config['search'].get('filters', dict())
        self.display_columns = config.get('display', {}).get('columns', ['*'])
class DatabaseSearch:
    def __init__(self, schema: DatabaseSchema):
        self.schema = schema
    
    def search(self, field, value, mode, limit:int = 10, desired_columns:list = ['*'], filters: dict = dict()):
        columns = ', '.join(desired_columns)
        table = self.schema.table

        if mode == 'exact':
            query = f'SELECT {columns} FROM {table} WHERE {field}=? LIMIT ?'
            params = (value, limit)
        elif mode == 'exact_nocase':
            query = f'SELECT {columns} FROM {table} WHERE {field}=? COLLATE NOCASE LIMIT ?'
            params = (value, limit)
        elif mode == 'like':
            filters_list = []
            filter_value = []
            for filtr in filters.keys():
                mode = filters[filtr]['mode']
                if mode == 'equal':
                    sign = '='
                elif mode == 'less than':
                    sign = '<'
                elif mode == 'greater than':
                    sign = '>'
                filters_list.append(f'AND {filtr}{sign}?')
                filter_value.append(filters[filtr]['value'])
            query = f'''
                SELECT {columns} FROM {table} WHERE {field} LIKE ?
                {'\n'.join(filters_list)}
                LIMIT ?
            '''
            params = (value, *filter_value, limit)
        elif mode == 'fts':
            filters_list = []
            filter_value = []
            for filtr in filters.keys():
                mode = filters[filtr]['mode']
                if mode == 'equal':
                    sign = '='
                elif mode == 'less than':
                    sign = '<'
                elif mode == 'greater than':
                    sign = '>'
                filters_list.append(f'AND {filtr}{sign}?')
                filter_value.append(filters[filtr]['value'])

            fts_table = self.schema.search_columns[field]['fts_table']
            query = f'''
                SELECT {columns} FROM {table} WHERE ROWID in
                (SELECT ROWID FROM {fts_table} WHERE {field} LIKE ?)
                {'\n'.join(filters_list)}
                LIMIT ?
            '''
            params = (value, *filter_value, limit)
        else:
            raise ValueError(f'Unknown search mode: {mode}')

        with DatabaseConnection(self.schema.location) as cur:
            cur.execute(query, params)
            results = cur.fetchall()
            return results

def clear_terminal():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

# get user input
def get_input(text: str):
    inp = input(text)
    if inp == 'q' or inp == 'quit' or inp == '0' or inp == '':
        clear_terminal()
        quit()
    return inp

# prompt user to choose
def select(choices: list, kind: str = ''):
    clear_terminal()
    if len(choices) == 1:
        return choices[0]
    print(f'Available {kind}s:')
    for i,choice in enumerate(choices, start=1):
        print(f'\t{i}. {choice}')
    choice = int(get_input(f'Select {kind} number: '))
    choice = choices[choice-1]
    return choice

def select_filters(filters_schema: dict):
    filters = dict()
    use_filters = get_input('Search using filters? (y/n)')
    if use_filters == 'n': return dict()
    while True:
        filtr = select(list(filters_schema.keys()), 'filter')
        mode = select(filters_schema[filtr]['modes'], 'filter mode')
        value = select_value(filtr, mode)
        filters[filtr] = {'mode': mode, 'value': value}
        add_filters = get_input('Use more filters? (y/n)')
        if add_filters == 'n': break
    return filters

def select_value(field: str, filter_mode: str = None):
    value = get_input(f'Enter {field}\'s value to search: ') if not filter_mode else get_input(f'Enter {field}\'s value to be {filter_mode}: ')
    return value

def display_data(results, headers):
    zipped = []
    for i,result in enumerate(results, start=1):
        record = dict()
        for field,value in zip(headers, result):
            record[field] = value
        zipped.append(record)
    return zipped
            
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
    with open('config.json', 'r') as f:
        databases = json.load(f)

    db_key = select(list(databases.keys()), 'database')
    schema = DatabaseSchema(db_key, databases[db_key])
    searcher = DatabaseSearch(schema)
    
    field = select(list(schema.search_columns.keys()), 'field')
    mode = select(schema.search_columns[field]['modes'], 'mode')
    value = select_value(field)
    filters = dict()
    if mode == 'like':
        filters = select_filters(schema.search_filters)
    elif mode == 'fts':
        value = '%' + value.replace(' ', '%') + '%'
        filters = select_filters(schema.search_filters)
    else:
        pass

    results = searcher.search(field, value, mode, limit=20, filters=filters, desired_columns=schema.display_columns)
    headers = []
    for header in schema.display_columns:
        if ' AS ' in header:
            alias = header.split(' AS ')[-1].strip()
            if alias.startswith('\"') and alias.endswith('\"'):
                alias = alias[1:-1]
            elif alias.startswith('\'') and alias.endswith('\''):
                alias = alias[1:-1]
            headers.append(alias)
        else:
            headers.append(header.strip())
    displayable = display_data(results, headers)
    display(displayable)
    clear_terminal()
