import marimo

__generated_with = "0.10.5"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    # Environment and Data Handle
    import os
    import boto3
    from botocore.exceptions import ClientError
    import awswrangler as wr
    from dotenv import load_dotenv
    import pandas as pd

    # Data Viz
    import altair as alt
    return ClientError, alt, boto3, load_dotenv, mo, os, pd, wr


@app.cell(hide_code=True)
def _(boto3, load_dotenv, os):
    # Load environment variables from .env file
    load_dotenv()

    session = boto3.Session(
        region_name=os.getenv('REGION_NAME'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

    database = 'mtb_datasus'
    return database, session


@app.cell(hide_code=True)
def _(session, wr):
    # # CID List
    # cid_query = "SELECT id_cid FROM mtb_datasus.sig_dim_cid"
    # df_cid = query_athena(cid_query, database, session)

    cid_s3_path = 's3://marimo-test/filter_data/cid_list.parquet'

    # # Write the DataFrame to a Parquet file on S3
    # wr.s3.to_parquet(
    #     df=df_cid,
    #     path=cid_s3_path,
    #     boto3_session=session
    # )

    df_cid = wr.s3.read_parquet(
        path=cid_s3_path,
        boto3_session=session
    )
    return cid_s3_path, df_cid


@app.cell(hide_code=True)
def _(session, wr):
    # Procedimento List
    # procedimento_query = "SELECT CAST(id_procedimento AS VARCHAR) as id_procedimento FROM mtb_datasus.sig_dim_procedimento"
    # df_procedimento = query_athena(procedimento_query, database, session)

    procedimento_s3_path = 's3://marimo-test/filter_data/procedimento_list.parquet'

    # # Write the DataFrame to a Parquet file on S3
    # wr.s3.to_parquet(
    #     df=df_procedimento,
    #     path=procedimento_s3_path,
    #     boto3_session=session
    # )

    df_procedimento = wr.s3.read_parquet(
        path=procedimento_s3_path,
        boto3_session=session
    )
    return df_procedimento, procedimento_s3_path


@app.cell(hide_code=True)
def _(mo):
    query_params = mo.query_params()
    return (query_params,)


@app.cell(hide_code=True)
def _(df_cid, df_procedimento, mo, query_params):
    years_dropdown = mo.ui.number(start=1, stop=5, step=1, label="Últimos anos: ")

    cid = mo.ui.multiselect(
        df_cid['id_cid'].to_list(),
        value=query_params["cid"] or None,
        on_change=lambda value: query_params.set("cid", value),
        label="CID: ",
        max_selections=5
    )

    procedimento_dropdown = mo.ui.multiselect(
        df_procedimento['id_procedimento'].to_list(),
        label="Procedimento: ",
        max_selections=5
    )

    mo.hstack(
        [years_dropdown, cid, procedimento_dropdown],
        align="center",
        widths="equal"
    )
    return cid, procedimento_dropdown, years_dropdown


@app.cell(hide_code=True)
def _(cid, mo, procedimento_dropdown):
    mo.stop(not len(cid.value))

    if isinstance(cid.value, list):
        cid_string = "'"+"','".join(cid.value)+"'"
    else:
        cid_string = "'"+cid.value+"'"

    if isinstance(procedimento_dropdown.value, list):
        procedimento_string = "'"+"','".join(procedimento_dropdown.value)+"'"
    if isinstance(procedimento_dropdown.value, str):
        procedimento_string = "'"+procedimento_dropdown.value+"'"
    else:
        procedimento_string = ''

    return cid_string, procedimento_string


@app.cell(hide_code=True)
def _(procedimento_dropdown, wr):
    def curated_query(query_raw):
        """
        Function to replace non-mandatory filters 
        in case they're empty.
        """
        if procedimento_dropdown.value == []:
            new_query = query_raw.replace("sig_dim_procedimento.id_procedimento in ('')", "1=1")
        else:
            new_query = query_raw
        return new_query

    def query_athena(query, database, session):
        """
        Function to query on AWS Athena
        """
        _query = curated_query(query)
        df = wr.athena.read_sql_query(
            sql=_query,
            database=database,
            boto3_session=session
        )
        return df
    return curated_query, query_athena


@app.cell(hide_code=True)
def _(cid_string, procedimento_string, years_dropdown):
    query_n_internacoes =f"""
    with ultimo_ano_publicacao as (
        select dt_max_ano as max_ano_publicacao
        from mtb_datasus.max_date_datasus
        where base_origem = 'sihsus'
    )
    , internacoes_foco as (
        select distinct id_aih
        from mtb_datasus.sih_fato_rd_internacoes
        where 1 = 1
        --and substring(id_motivo_saida_permanencia, 1, 1) in('1', '4', '5', '6') --1) Alta, 4) Óbito, 5) Outros, 6) Parto (Excluídos Permanência/Transferência)
        and exists (select 1 from mtb_datasus.sih_fato_internacao_cid
                    join  mtb_datasus.sig_dim_cid on mtb_datasus.sih_fato_internacao_cid.cid = mtb_datasus.sig_dim_cid.id_cid
                    where sig_dim_cid.id_cid in ({cid_string})
                    and sih_fato_internacao_cid.id_aih = sih_fato_rd_internacoes.id_aih)
        and exists (select 1 from mtb_datasus.sih_fato_internacao_procedimento
                    join mtb_datasus.sig_dim_procedimento on sih_fato_internacao_procedimento.id_procedimento = sig_dim_procedimento.id_procedimento
                    where sig_dim_procedimento.id_procedimento in ({procedimento_string})
                    and sih_fato_internacao_procedimento.id_aih = sih_fato_rd_internacoes.id_aih)
        and (select max_ano_publicacao from ultimo_ano_publicacao) - year(dt_entrada_internacao) <= {years_dropdown.value}
    )
    select count(id_aih) as n_internacoes from internacoes_foco
    """
    return (query_n_internacoes,)


@app.cell(hide_code=True)
def _(cid_string, procedimento_string, years_dropdown):
    query_custo_medio =f"""
    with ultimo_ano_publicacao as (
        select dt_max_ano as max_ano_publicacao
        from mtb_datasus.max_date_datasus
        where base_origem = 'sihsus'
    )
    , internacoes_foco as (
        select 
            distinct(id_aih),
            sum(vl_total_aih) as valor_total_aih_real
        from mtb_datasus.sih_fato_rd_internacoes
        where (id_motivo_saida_permanencia / 10) in (1, 4, 5, 6)
        and exists (select 1 from mtb_datasus.sih_fato_internacao_cid
                    join  mtb_datasus.sig_fato_cid on mtb_datasus.sih_fato_internacao_cid.cid = mtb_datasus.sig_fato_cid.id_cid
                    where sih_fato_internacao_cid.cid in ({cid_string})
                    and sih_fato_internacao_cid.id_aih = sih_fato_rd_internacoes.id_aih)
        and exists (select 1 from mtb_datasus.sih_fato_internacao_procedimento
                    join mtb_datasus.sig_dim_procedimento on sih_fato_internacao_procedimento.id_procedimento = sig_dim_procedimento.id_procedimento
                    where sig_dim_procedimento.id_procedimento in ({procedimento_string})
                    and sih_fato_internacao_procedimento.id_aih = sih_fato_rd_internacoes.id_aih)
        and (select max_ano_publicacao from ultimo_ano_publicacao) - year(sih_fato_rd_internacoes.dt_entrada_internacao) <= {years_dropdown.value}
        group by id_aih
    )
    select sum(valor_total_aih_real)/count(distinct id_aih) as media_custo_internacao
    from internacoes_foco
    """
    return (query_custo_medio,)


@app.cell(hide_code=True)
def _(cid_string, procedimento_string, years_dropdown):
    query_internacoes_ano = f"""
    with ultimo_ano_publicacao as (
        select dt_max_ano as max_ano_publicacao
        from mtb_datasus.max_date_datasus
        where base_origem = 'sihsus'
    )
    , internacoes_foco as (
        select distinct id_aih
        from mtb_datasus.sih_fato_rd_internacoes
        where 1 = 1
        --and substring(id_motivo_saida_permanencia, 1, 1) in('1', '4', '5', '6') --1) Alta, 4) Óbito, 5) Outros, 6) Parto (Excluídos Permanência/Transferência)
        and exists (select 1 from mtb_datasus.sih_fato_internacao_cid
                    join  mtb_datasus.sig_dim_cid on mtb_datasus.sih_fato_internacao_cid.cid = mtb_datasus.sig_dim_cid.id_cid
                    where sig_dim_cid.id_cid in ({cid_string})
                    and sih_fato_internacao_cid.id_aih = sih_fato_rd_internacoes.id_aih)
        and exists (select 1 from mtb_datasus.sih_fato_internacao_procedimento
                      join mtb_datasus.sig_dim_procedimento on sig_dim_procedimento.id_procedimento = sih_fato_internacao_procedimento.id_procedimento
                    where sig_dim_procedimento.id_procedimento in ({procedimento_string})
                    and sih_fato_internacao_procedimento.id_aih = sih_fato_rd_internacoes.id_aih)              
        and (select max_ano_publicacao from ultimo_ano_publicacao) - cast(sih_fato_rd_internacoes.partition_0 as int) <= {years_dropdown.value}
    )
    , internacao_obito as (
    select 
        id_aih,
        id_motivo_saida_permanencia,
        ind_obito,
        case 
            when ind_obito = 1 then '3. Óbito' 
            when mtb_datasus.sih_fato_rd_internacoes.id_motivo_saida_permanencia/10 in (1, 4, 5, 6) then '1. Alta'
            else '2. Permanência'
            end alta_obito,
            date_trunc('month',sih_fato_rd_internacoes.dt_entrada_internacao) as data_internacao
        from mtb_datasus.sih_fato_rd_internacoes
        where exists (
            select 1=1
            from internacoes_foco
            where internacoes_foco.id_aih = mtb_datasus.sih_fato_rd_internacoes.id_aih
            )
    )
    select 
        year(data_internacao) as ano_internacao,
        count(distinct id_aih) as qtde_internacoes
    from internacao_obito
    group by year(data_internacao)
    """
    return (query_internacoes_ano,)


@app.cell(hide_code=True)
def _(cid_string, procedimento_string, years_dropdown):
    query_amb_pacientes_coorte = f"""
    WITH
      ultimo_ano_publicacao AS (
        SELECT
          dt_max_ano
        FROM
          mtb_datasus.max_date_datasus
        WHERE
          frente = 'ambulatorial'
      ),
      producao_de_interesse AS (
        SELECT
          mtb_datasus.sia_fato_producao_paciente.id_cns_paciente
        FROM
          mtb_datasus.sia_fato_producao_paciente
          LEFT JOIN mtb_datasus.sig_dim_cid ON mtb_datasus.sia_fato_producao_paciente.id_cid_principal = sig_dim_cid.id_cid
          LEFT JOIN mtb_datasus.sia_dim_sexo_paciente ON mtb_datasus.sia_fato_producao_paciente.id_cns_paciente = mtb_datasus.sia_dim_sexo_paciente.id_cns_paciente
          LEFT JOIN mtb_datasus.sia_dim_raca_cor_paciente ON mtb_datasus.sia_fato_producao_paciente.id_cns_paciente = mtb_datasus.sia_dim_raca_cor_paciente.id_cns_paciente
          LEFT JOIN mtb_datasus.cnes_dim_cep_paciente ON mtb_datasus.cnes_dim_cep_paciente.id_municipio = mtb_datasus.sia_fato_producao_paciente.id_municipio_paciente
          LEFT JOIN mtb_datasus.cnes_dim_cep_estabelecimento ON mtb_datasus.cnes_dim_cep_estabelecimento.id_municipio = mtb_datasus.sia_fato_producao_paciente.id_municipio_estabelecimento
          LEFT JOIN mtb_datasus.sig_dim_procedimento ON mtb_datasus.sig_dim_procedimento.id_procedimento = mtb_datasus.sia_fato_producao_paciente.id_procedimento_principal
        WHERE
          sig_dim_cid.id_cid in ({cid_string})
          AND sig_dim_procedimento.id_procedimento in ({procedimento_string})
          AND (select dt_max_ano from ultimo_ano_publicacao) - year(dt_atendimento) <= {years_dropdown.value}
      ),
      data_diagnostico AS (
        SELECT
          id_cns_paciente,
          min(dt_atendimento) AS data_diagnostico
        FROM
          mtb_datasus.sia_fato_producao_paciente
          LEFT JOIN mtb_datasus.sig_dim_cid ON mtb_datasus.sia_fato_producao_paciente.id_cid_principal = mtb_datasus.sig_dim_cid.id_cid
          LEFT JOIN mtb_datasus.sig_dim_procedimento ON mtb_datasus.sia_fato_producao_paciente.id_procedimento_principal = mtb_datasus.sig_dim_procedimento.id_procedimento
        WHERE
          sig_dim_cid.id_cid in ({cid_string})
          AND sig_dim_procedimento.id_procedimento in ({procedimento_string})
        GROUP BY
          id_cns_paciente
      ),
      sumario_pcn_idade AS (
        SELECT
          idade_pcn_meses.id_cns_paciente,
          faixa_etaria_ibge AS faixa_etaria_diagnostico
        FROM
          (
            SELECT DISTINCT
              sip.id_cns_paciente,
              date_diff ('month', sip.data_nascimento, da.data_diagnostico) AS idade_meses
            FROM
              mtb_datasus.sia_dim_idade_paciente AS sip
              INNER JOIN data_diagnostico AS da ON sip.id_cns_paciente = da.id_cns_paciente
          ) AS idade_pcn_meses
          INNER JOIN mtb_datasus.dim_faixas_etarias_meses ON idade_pcn_meses.idade_meses = dim_faixas_etarias_meses.idade_meses
      )
    SELECT
      count(DISTINCT sumario_pcn_idade.id_cns_paciente) AS qt_pacientes
    FROM
      producao_de_interesse
      LEFT JOIN sumario_pcn_idade ON sumario_pcn_idade.id_cns_paciente = producao_de_interesse.id_cns_paciente
    """
    return (query_amb_pacientes_coorte,)


@app.cell(hide_code=True)
def _(cid_string, procedimento_string, years_dropdown):
    query_amb_pacientes_ano = f"""
    with ultimo_ano_publicacao as (
    select dt_max_ano
    from mtb_datasus.max_date_datasus
    where frente = 'ambulatorial'
    ) 
    , producao_de_interesse as (
        select mtb_datasus.sia_fato_producao_paciente.id_cns_paciente as id_cns_paciente
            , dt_atendimento
        from mtb_datasus.sia_fato_producao_paciente
        left join  mtb_datasus.sig_dim_cid                     on mtb_datasus.sia_fato_producao_paciente.id_cid_principal = mtb_datasus.sig_dim_cid.id_cid
        left join  mtb_datasus.sia_dim_sexo_paciente           on mtb_datasus.sia_fato_producao_paciente.id_cns_paciente = mtb_datasus.sia_dim_sexo_paciente.id_cns_paciente
        left join  mtb_datasus.sia_dim_raca_cor_paciente       on mtb_datasus.sia_fato_producao_paciente.id_cns_paciente = mtb_datasus.sia_dim_raca_cor_paciente.id_cns_paciente
        left join  mtb_datasus.cnes_dim_cep_paciente            on mtb_datasus.cnes_dim_cep_paciente.id_municipio           = mtb_datasus.sia_fato_producao_paciente.id_municipio_paciente
        left join  mtb_datasus.cnes_dim_cep_estabelecimento     on mtb_datasus.cnes_dim_cep_estabelecimento.id_municipio    = mtb_datasus.sia_fato_producao_paciente.id_municipio_estabelecimento
        left join  mtb_datasus.sig_dim_procedimento            on mtb_datasus.sig_dim_procedimento.id_procedimento = mtb_datasus.sia_fato_producao_paciente.id_procedimento_principal

        where sig_dim_cid.id_cid in ({cid_string})
        and sig_dim_procedimento.id_procedimento in ({procedimento_string})
        and (select dt_max_ano from ultimo_ano_publicacao) - year(dt_atendimento)  <= {years_dropdown.value}
    )
    , data_diagnostico as (
        select 
              id_cns_paciente
            , min(dt_atendimento) as data_diagnostico
        from mtb_datasus.sia_fato_producao_paciente
        left join mtb_datasus.sig_dim_cid              on mtb_datasus.sia_fato_producao_paciente.id_cid_principal=mtb_datasus.sig_dim_cid.id_cid
        left join mtb_datasus.sig_dim_procedimento     on mtb_datasus.sia_fato_producao_paciente.id_procedimento_principal=mtb_datasus.sig_dim_procedimento.id_procedimento
        where sig_dim_cid.id_cid in ({cid_string})
        and sig_dim_procedimento.id_procedimento in ({procedimento_string})
        group by id_cns_paciente
    )
    , sumario_pcn_idade as (
        select idade_pcn_meses.id_cns_paciente, faixa_etaria_ibge as faixa_etaria_diagnostico
        from (  select distinct sip.id_cns_paciente, date_diff('month', sip.data_nascimento, da.data_diagnostico) as idade_meses
                from        mtb_datasus.sia_dim_idade_paciente  as sip
                inner join  data_diagnostico                as da on sip.id_cns_paciente = da.id_cns_paciente
            ) as idade_pcn_meses
        inner join  mtb_datasus.dim_faixas_etarias_meses on idade_pcn_meses.idade_meses=mtb_datasus.dim_faixas_etarias_meses.idade_meses 
    )
        select year(dt_atendimento) as ano_atendimento
            , count(distinct producao_de_interesse.id_cns_paciente) as qt_pacientes
        from producao_de_interesse
        left join sumario_pcn_idade on sumario_pcn_idade.id_cns_paciente=producao_de_interesse.id_cns_paciente
        group by year(dt_atendimento)
    order by year(dt_atendimento)

    """
    return (query_amb_pacientes_ano,)


@app.cell(hide_code=True)
def _(database, query_athena, query_n_internacoes, session):
    df_n_internacoes = query_athena(query_n_internacoes, database, session)
    return (df_n_internacoes,)


@app.cell(hide_code=True)
def _(database, query_athena, query_custo_medio, session):
    df_custo_medio = query_athena(query_custo_medio, database, session)
    return (df_custo_medio,)


@app.cell(hide_code=True)
def _(database, query_athena, query_internacoes_ano, session):
    df_internacoes_ano = query_athena(query_internacoes_ano, database, session)
    return (df_internacoes_ano,)


@app.cell(hide_code=True)
def _(database, query_amb_pacientes_coorte, query_athena, session):
    df_amb_pacientes_coorte = query_athena(query_amb_pacientes_coorte, database, session)
    return (df_amb_pacientes_coorte,)


@app.cell(hide_code=True)
def _(database, query_amb_pacientes_ano, query_athena, session):
    df_amb_pacientes_ano = query_athena(query_amb_pacientes_ano, database, session)
    return (df_amb_pacientes_ano,)


@app.cell(hide_code=True)
def _(df_amb_pacientes_coorte, df_custo_medio, df_n_internacoes, mo):
    kpi_amb_pacientes_coorte = mo.stat(
        label="Quantidade pacientes no coorte",
        bordered=True,
        value=f"{df_amb_pacientes_coorte.iloc[0,0]:,.0f}",

    )

    kpi_n_internacoes = mo.stat(
        label="Quantidade de internações",
        bordered=True,
        value=f"{df_n_internacoes.iloc[0,0]:,.0f}",
    )

    kpi_custo_medio = mo.stat(
        label="Custo médio de internação",
        bordered=True,
        value=f"R${df_custo_medio.iloc[0,0]:,.2f}",
    )
    return kpi_amb_pacientes_coorte, kpi_custo_medio, kpi_n_internacoes


@app.cell(hide_code=True)
def _(
    alt,
    df_amb_pacientes_ano,
    df_internacoes_ano,
    kpi_amb_pacientes_coorte,
    kpi_custo_medio,
    kpi_n_internacoes,
    mo,
):
    cht_amb_pacientes_ano = mo.ui.altair_chart(
        (
            alt.Chart(df_amb_pacientes_ano)
            .mark_bar()
            .encode(x="ano_atendimento:O", y="qt_pacientes:Q")
        ),
        chart_selection="point",
        legend_selection=False,
        label="Pacientes por ano",
    )

    cht_internacoes_ano = mo.ui.altair_chart(
        (
            alt.Chart(df_internacoes_ano)
            .mark_bar()
            .encode(x="ano_internacao:O", y="qtde_internacoes:Q")
        ),
        chart_selection="point",
        legend_selection=False,
        label="Internações por ano",
    )

    mo.vstack([kpi_amb_pacientes_coorte,
              cht_amb_pacientes_ano])

    mo.ui.tabs(
        {
            "::lucide:chart-column-big:: Ambulatorial": mo.vstack(
                [kpi_amb_pacientes_coorte, cht_amb_pacientes_ano]
            ),
            "::lucide:chart-column-big:: Hospitalar": mo.vstack(
                [mo.hstack(
                    [kpi_n_internacoes, kpi_custo_medio],
                    widths="equal",
                    gap=1,
                ),
                 cht_internacoes_ano]
            ),
        }
    )
    return cht_amb_pacientes_ano, cht_internacoes_ano


@app.cell(hide_code=True)
def _(
    cht_amb_pacientes_ano,
    cht_internacoes_ano,
    kpi_amb_pacientes_coorte,
    kpi_custo_medio,
    kpi_n_internacoes,
    mo,
):
    mo.hstack([
        mo.vstack([kpi_amb_pacientes_coorte, cht_amb_pacientes_ano]),
        mo.vstack([mo.hstack(
                    [kpi_n_internacoes, kpi_custo_medio],
                    widths="equal",
                    gap=1,
                ),
                 cht_internacoes_ano])
    ],
        widths="equal",
        gap=1,
    )
    return


if __name__ == "__main__":
    app.run()
