from gspread_dataframe import get_as_dataframe, set_with_dataframe


def export_to_sheets(spreadsheet, sheet_name, df, mode='r'):
    ws = spreadsheet.worksheet(f'{sheet_name}')
    if (mode == 'w'):
        ws.clear()
        set_with_dataframe(worksheet=ws, dataframe=df, include_index=False,
                           include_column_header=True, resize=False)
        return True
    elif (mode == 'a'):
        ws.add_rows(df.shape[0])
        max_rows = len(ws.get_all_values(major_dimension='rows'))
        set_with_dataframe(worksheet=ws, dataframe=df, include_index=False,
                           include_column_header=False, row=max_rows + 1,
                           resize=False)
        return True
    else:
        return get_as_dataframe(worksheet=ws)
