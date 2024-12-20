import marimo

__generated_with = "0.10.5"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    return mo, pd


@app.cell
def _(mo):
    query_params = mo.query_params()
    return (query_params,)


@app.cell
def _(mo, query_params):
    search = mo.ui.text(
        value=query_params["search"] or "",
        on_change=lambda value: query_params.set("search", value),
    )
    search
    return (search,)


@app.cell
def _(search):
    _s = f'Teste output search: {search}'
    _s
    return


@app.cell
def _():
    return


@app.cell
def _(mo, query_params):
    l = ['M32','G121','G122']
    test_drop = mo.ui.multiselect(
        l,
        value=query_params["test_drop"] or "",
        on_change=lambda value: query_params.set("test_drop", value),
        full_width=True
    )
    test_drop
    return l, test_drop


@app.cell
def _(query_params):
    s = f'Teste output: {query_params["test_drop"]}, type: {type(query_params["test_drop"])}'
    s
    return (s,)


@app.cell
def _():
    # toggle = mo.ui.switch(label="Toggle me")
    # toggle
    return


@app.cell
def _():
    # query_params["test_drop"] = test_drop.value
    return


@app.cell
def _(pd):
    json_data = [
        {"name": "Alice", "age": 25, "city": "New York", "cid": "M32"},
        {"name": "Bob", "age": 30, "city": "San Francisco", "cid": "G121"},
        {"name": "Charlie", "age": 35, "city": "Los Angeles", "cid": "G122"}
    ]
    df = pd.DataFrame(json_data)
    df
    return df, json_data


@app.cell
def _(query_params):
    try:
        if isinstance(query_params['test_drop'], list):
            cid_string = "'"+"','".join(query_params['test_drop'])+"'"
        else:
            cid_string = "'"+query_params['test_drop']+"'"
    except:
        cid_string = "''"
    print(cid_string)
    return (cid_string,)


@app.cell
def _(cid_string, df, mo):
    _df = mo.sql(
        f"""
        SELECT * FROM df
        where cid in ({cid_string})
        """
    )
    return


if __name__ == "__main__":
    app.run()
