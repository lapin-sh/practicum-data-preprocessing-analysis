# Предподготовка и анализ данных

Проекты по курсу Яндекс Практикума и курсовая работа.

| Проект | Материалы |
| --- | --- |
| Исследование надёжности заёмщиков | [Ноутбук с предобработкой и анализом](borrowers/borrowers_reliability.ipynb), [код первой части для тренажёра](borrowers/part1_trainer.txt) |
| Исследование объявлений о продаже квартир | [Ноутбук с анализом цены квартир](real-estate/real_estate_analysis.ipynb) |
| Продажи автомобилей в Казахстане и позиция «Меркур Авто» | [Отчёт](coursework/report.md), [очищенный CSV](coursework/autokz2019_cleaned.csv), [скрипт очистки](coursework/clean_autokz.py), [ноутбук с анализом](coursework/autokz2019_analysis.ipynb) |

## Воспроизведение

Для ноутбуков нужны Python, Jupyter, pandas, NumPy, Matplotlib и SciPy. Запускайте ячейки по порядку из папки соответствующего проекта. При наличии локального CSV ноутбуки используют его. Иначе они читают исходные данные по ссылкам Практикума.

- [data.csv](https://code.s3.yandex.net/datasets/data.csv)
- [real_estate_data.csv](https://code.s3.yandex.net/datasets/real_estate_data.csv)
- [autokz2019.csv](https://code.s3.yandex.net/high-education_higher-data-analytics/autokz2019.csv)

Чтобы заново получить очищенный CSV курсовой, выполните `python clean_autokz.py` из папки `coursework`. Скрипт сохраняет `autokz2019_cleaned.csv` в этой же папке.
