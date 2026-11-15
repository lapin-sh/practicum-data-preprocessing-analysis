"""Подготовка данных о продажах автомобилей из выгрузки Практикума."""

from argparse import ArgumentParser
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

SOURCE_URL = (
    'https://code.s3.yandex.net/high-education_higher-data-analytics/'
    'autokz2019.csv'
)
MERCUR = 'Mercur Auto'

COLUMNS = {
    'Компания': 'company',
    'Бренд': 'brand',
    'Модель': 'model',
    'Год выпуска': 'model_year',
    'Страна-производитель': 'country_code',
    'Вид топлива': 'fuel_type',
    'Объём двиг, л,': 'engine_l',
    'Коробка передач': 'transmission',
    'Тип привода': 'drive_type',
    'Регион': 'region',
    'Количество': 'quantity',
    'Цена, USD': 'unit_price_usd',
    'Продажа, USD': 'sales_usd',
    'Область': 'oblast',
    'Сегментация 2013': 'segment_2013',
    'Класс 2013': 'class_2013',
}
DROPPED = (
    'Наименование дилерского центра', 'Форма расчета', 'Сегмент', 'Сегмент ЕПР',
    'Локализация производства', 'Тип клиента', 'Модификация', 'Сегментация Eng',
)
CATEGORY_COLUMNS = ['fuel_type', 'transmission', 'drive_type', 'segment_2013', 'class_2013']
MONTHS = {
    month: number
    for number, month in enumerate(
        'январь февраль март апрель май июнь июль август сентябрь октябрь ноябрь декабрь'.split(),
        start=1,
    )
}

COUNTRIES = {
    'австрия': 'AUT', 'бельгия': 'BEL', 'белоруссия': 'BLR',
    'венгрия': 'HUN', 'германия': 'DEU', 'испания': 'ESP',
    'китай': 'CHN', 'корея': 'KOR', 'нидерланды': 'NLD', 'польша': 'POL',
    'республика казахстан': 'KAZ', 'российская федерация': 'RUS',
    'сша': 'USA', 'таиланд': 'THA', 'турция': 'TUR',
    'узбекистан': 'UZB', 'швеция': 'SWE', 'япония': 'JPN', 'uk': 'GBR',
}
COMPANIES = {
    'mercur auto': MERCUR, 'mercur autos': MERCUR, 'меркур авто': MERCUR,
    'astana motors': 'Astana Motors',
    'автокапитал': 'Autokapital', 'autokapital': 'Autokapital',
    'каспиан моторс': 'Caspian Motors', 'caspian motors': 'Caspian Motors',
    'ммс рус': 'ММС Рус', 'mmc rus': 'ММС Рус',
    'равон моторс казахстан': 'Равон Моторс Казахстан',
    'ravon motors kazakstan': 'Равон Моторс Казахстан',
    'хино моторс казахстан': 'Хино Моторс Казахстан', 'hino motors': 'Хино Моторс Казахстан',
}
FUELS = {
    'бензин': 'F', 'дизель': 'D', 'электро': 'E',
    'электричество': 'E', 'гибрид': 'HYB',
}
DRIVES = {
    '4wd': '4WD', 'awd': '4WD', 'полный': '4WD', 'полныйпривод': '4WD',
    'quattro': '4WD', '4motion': '4WD', '4x4': '4WD',
    '2wd': '2WD', '4x2': '2WD', '4x2.2': '2WD',
    'ff': 'FWD', 'fwd': 'FWD', 'передний': 'FWD', 'передний(ff)': 'FWD',
    'rwd': 'RWD', 'задний': 'RWD',
}


def tidy_text(values):
    return values.astype('string').str.strip().str.replace(r'\s+', ' ', regex=True)


def normalize_key(values):
    return tidy_text(values).str.casefold()


def read_sales(source):
    """Загрузить архив, в котором разделитель — точка с запятой, а дробная часть отделена запятой."""
    csv_options = {
        'sep': ';', 'decimal': ',', 'encoding': 'utf-8-sig', 'low_memory': False,
    }
    try:
        curl = which('curl')
        if isinstance(source, str) and source.startswith('https://') and curl:
            with TemporaryDirectory() as directory:
                downloaded = Path(directory) / 'autokz2019.csv'
                run([curl, '-fsSL', '--connect-timeout', '10', '--max-time', '120',
                     '--output', str(downloaded), source], check=True)
                return pd.read_csv(downloaded, **csv_options)
        return pd.read_csv(source, **csv_options)
    except (OSError, CalledProcessError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise ValueError(f'Не удалось прочитать выгрузку {source}. Проверьте путь или используйте локальный autokz2019.csv.') from error


def transmission_type(values):
    normalized = normalize_key(values)
    labels = normalized.str.translate(str.maketrans('атм', 'atm'))
    labels = labels.str.replace(r'[\s/\-]+', '', regex=True)
    manual = labels.str.fullmatch(r'\d*m(?:t)?|mех\.|mкпп?', na=False)
    auto = (
        labels.str.fullmatch(r'\d*a(?:t)?|\d*amt', na=False)
        | labels.str.contains(r'aкп|cvt|dsg|dct|pdk|tronic|powershift', na=False)
        | normalized.eq('редуктор').fillna(False)
    )
    types = pd.Series(pd.NA, index=values.index, dtype='string')
    types.loc[manual] = 'Механика'
    types.loc[auto] = 'Автомат'
    return types


def clean_sales(raw, *, drop_exact=True):
    """Вернуть очищенные операции и счётчики преобразований."""
    required = {'Год', 'Месяц', 'Модификация'} | set(COLUMNS)
    missing_columns = required.difference(raw.columns)
    if missing_columns:
        raise ValueError(f'Нет ожидаемых столбцов: {", ".join(sorted(missing_columns))}')

    nonempty = raw.dropna(how='all')
    exact = nonempty.duplicated()
    # Сравниваем исходные колонки. После удаления модификации и дилера
    # разные операции могут стать внешне одинаковыми.
    sales = (nonempty.loc[~exact] if drop_exact else nonempty).copy()
    trim = normalize_key(sales['Модификация'])
    sales = sales.drop(columns=list(DROPPED), errors='ignore').rename(columns=COLUMNS)

    year = pd.to_numeric(sales['Год'], errors='raise')
    month = normalize_key(sales['Месяц']).map(MONTHS)
    if year.isna().any() or month.isna().any():
        raise ValueError('Для части строк месяц или год продажи не распознан.')
    sales['sale_date'] = pd.to_datetime({'year': year, 'month': month, 'day': 1}) + pd.offsets.MonthEnd(0)

    company = tidy_text(sales['company'])
    sales['company'] = company.str.casefold().map(COMPANIES).fillna(company)
    for column in ['brand', 'model', 'segment_2013', 'class_2013']:
        sales[column] = tidy_text(sales[column])
    for column in ['region', 'oblast']:
        sales[column] = tidy_text(sales[column]).str.replace(r'\.(?=\S)', '. ', regex=True).str.title()

    country = normalize_key(sales['country_code'])
    sales['country_code'] = country.map(COUNTRIES).astype('string')
    missing_country_codes = country.loc[country.notna() & sales['country_code'].isna()].unique()
    if len(missing_country_codes):
        raise ValueError(f'Добавьте коды ISO для стран: {", ".join(sorted(missing_country_codes))}')

    for column in ['quantity', 'unit_price_usd', 'sales_usd']:
        sales[column] = pd.to_numeric(sales[column], errors='raise')
    sales['quantity'] = sales['quantity'].astype('Int64')
    sales['model_year'] = pd.to_numeric(
        sales['model_year'].astype('string').str.replace(r'\s+', '', regex=True), errors='raise',
    ).astype('Int64')

    fuel = normalize_key(sales['fuel_type'])
    engine = normalize_key(sales['engine_l']).str.replace(',', '.', regex=False)
    gear = tidy_text(sales['transmission'])
    drive = normalize_key(sales['drive_type']).str.replace(' ', '', regex=False).str.replace('х', 'x')

    # У части Renault объём записан в топливе, коробка — в объёме.
    renault = sales['brand'].eq('Renault') & sales['model'].isin(['Duster', 'Sandero'])
    shifted = renault & fuel.isin(['2', '1,6']) & (engine.isin(['at', 'mt', '0']))
    gear.loc[shifted] = engine.loc[shifted]
    engine.loc[shifted] = fuel.loc[shifted].str.replace(',', '.', regex=False)
    fuel.loc[shifted] = pd.NA

    sales['fuel_type'] = fuel.map(FUELS).astype('string')
    electric_jaguar = sales['brand'].eq('Jaguar') & sales['model'].str.casefold().eq('i-pace')
    electric_jac = sales['brand'].str.casefold().eq('jac') & trim.eq('iev7s')
    hybrid_porsche = sales['brand'].eq('Porsche') & trim.str.contains('e-hybrid', na=False)
    # В выгрузке электромобиль iEV7S ошибочно помечен как бензиновый.
    sales.loc[electric_jaguar | electric_jac, 'fuel_type'] = 'E'
    sales.loc[hybrid_porsche, 'fuel_type'] = 'HYB'

    # Берём ведущий объём, отбрасывая маркировку L, MPI, GDI и т. п.
    engine_number = pd.to_numeric(engine.str.extract(r'^(\d+(?:\.\d+)?)', expand=False))
    niva = sales['brand'].eq('Chevrolet') & sales['model'].str.casefold().eq('niva')
    niva_errors = niva & engine_number.notna() & engine_number.ne(1.7)
    engine_number.loc[niva_errors] = 1.7
    polo_mpi = (
        sales['brand'].eq('Volkswagen') & sales['model'].eq('Polo')
        & trim.eq('polo comfortline mpi 81 квт (110 л.с.)')
    )
    isuzu_nmr85 = sales['brand'].eq('Isuzu') & sales['model'].eq('NMR') & trim.eq('isuzu nmr85')
    # Для этих двух модификаций значения 8,7 л расходятся с другими строками и спецификациями.
    polo_error = polo_mpi & engine_number.eq(8.7)
    nmr85_error = isuzu_nmr85 & engine_number.eq(8.7)
    engine_number.loc[polo_error] = 1.6
    engine_number.loc[nmr85_error] = 3.0
    electric = sales['fuel_type'].eq('E').fillna(False)
    sales['engine_l'] = engine_number.where(engine_number.gt(0) & ~electric).astype(float)

    # 2WD обозначает одну ведущую ось без уточнения, какую именно.
    sales['drive_type'] = drive.map(DRIVES)
    sales['transmission'] = transmission_type(gear)
    cayenne_eight = sales['brand'].eq('Porsche') & sales['model'].eq('Cayenne') & gear.eq('8')
    sales.loc[cayenne_eight, 'transmission'] = 'Автомат'

    sales[CATEGORY_COLUMNS] = sales[CATEGORY_COLUMNS].astype('category')
    sales = sales[['sale_date', *COLUMNS.values()]].reset_index(drop=True)

    calculated = sales['quantity'] * sales['unit_price_usd']
    known = calculated.notna()
    money_error = (sales.loc[known, 'sales_usd'] - calculated.loc[known]).abs()
    if (money_error.gt(.01).any() or sales['unit_price_usd'].le(0).any()
            or sales['sales_usd'].isna().any()):
        raise ValueError('Проверьте согласованность количества, цены и суммы продажи.')

    audit = {
        'Исходных строк': len(raw),
        'Полностью пустых строк': len(raw) - len(nonempty),
        'Удалено точных повторов': int(exact.sum()) if drop_exact else 0,
        'В итоговой таблице строк': len(sales),
        'Строк Renault с исправленным сдвигом полей': int(shifted.sum()),
        'Исправлено объёмов Chevrolet Niva': int(niva_errors.sum()),
        'Исправлено объёмов Volkswagen Polo': int(polo_error.sum()),
        'Исправлено объёмов Isuzu NMR85': int(nmr85_error.sum()),
        'Jaguar I-Pace без объёма ДВС': int(electric_jaguar.sum()),
        'Электромобилей JAC iEV7S': int(electric_jac.sum()),
        'Строк с неизвестным количеством': int(sales['quantity'].isna().sum()),
        'Возвратов': int(sales['quantity'].lt(0).sum()),
    }
    return sales, audit


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', help='Путь к исходному CSV')
    parser.add_argument('output', nargs='?', default='autokz2019_cleaned.csv', help='Путь для результата')
    args = parser.parse_args()
    local = Path('autokz2019.csv')
    source = args.input or (local if local.is_file() else SOURCE_URL)
    output = Path(args.output)
    if isinstance(source, Path) or not str(source).startswith(('https://', 'http://')):
        if output.resolve() == Path(source).resolve():
            parser.error('Пути исходного и итогового файлов должны отличаться.')

    sales, audit = clean_sales(read_sales(source))
    sales.to_csv(output, index=False, encoding='utf-8', date_format='%Y-%m-%d', lineterminator='\n')
    for item, value in audit.items():
        print(f'{item}: {value}')
    print(f'Итоговый CSV: {output}')


if __name__ == '__main__':
    main()
